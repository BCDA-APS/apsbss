"""Test the Scheduling Server API (some tests only work at APS)."""

import datetime
from contextlib import nullcontext as does_not_raise

import pytest

from ..bss_is import IS_BeamtimeRequest
from ..bss_is import IS_Exception
from ..bss_is import IS_MissingAuthentication
from ..bss_is import IS_NotAllowedToRespond
from ..bss_is import IS_SchedulingServer
from ..bss_is import IS_Unauthorized
from ..bss_is import User
from ..core import miner
from ._core import CREDS_FILE
from ._core import TEST_DATA_PATH
from ._core import is_aps_workstation
from ._core import yaml_loader

IS_BTR_77056_FILE = TEST_DATA_PATH / "is-gupId-77056.yml"


def test_IS_BeamtimeRequest():
    btr = IS_BeamtimeRequest({})
    assert btr.raw == {}
    assert not btr.current

    btr = IS_BeamtimeRequest(yaml_loader(IS_BTR_77056_FILE))
    assert len(btr.raw) == 23
    assert not btr.current
    assert miner(btr.raw, "beamtime.proposal.proposalType.display") == "PUP"

    user = btr._find_user("Andrew", "Allen")
    assert isinstance(user, list)
    assert len(user) == 1

    user = user[0]
    assert isinstance(user, User)
    assert user.firstName == "Andrew"
    assert user.lastName == "Allen"
    assert user.is_pi

    assert isinstance(btr.emails, list)
    assert len(btr.emails) == 6
    assert "andrew.allen@nist.gov" in btr.emails

    info = btr.info
    assert isinstance(info, dict)
    assert len(info) == 12
    assert info["run"] == "2022-2"
    assert info["PI Name"] != btr.pi
    assert info["PI Name"] == "Andrew Allen"
    assert info["PI affiliation"] == "National Institute of Standards and Technology (NIST)"
    assert info["PI email"] == "andrew.allen@nist.gov"
    assert info["PI badge"] == "85849"
    assert info["Proposal GUP"] == btr.proposal_id
    assert info["Proposal Title"] == btr.title
    assert info["Proposal PUP"] == 57504
    assert "capillary gas flow detector system;" in info["Equipment"]
    assert info["Start time"] == "2022-05-24 08:00:00-05:00"
    assert info["End time"] == "2022-10-01 00:00:00-05:00"
    assert info["Users"] == list(map(str, btr._users))  # [str(u) for u in btr._users]

    assert btr.pi == str(user)
    assert isinstance(btr.proposal_id, int), f"{type(btr.proposal_id)=!r}"
    assert btr.proposal_id == 77056

    assert btr.title == "USAXS/SAXS/WAXS Characterization at an MBA Storage Ring"

    assert isinstance(btr.users, list)
    assert len(btr.users) == 6
    assert "Andrew Allen" in btr.users

    summary = repr(btr)
    assert summary.startswith("IS_BeamtimeRequest(")
    assert summary.endswith(")")
    assert "id:77056" in summary
    assert "pi:'Andrew Allen <andrew.allen@nist.gov>'" in summary
    assert "title:'USAXS/SAXS/WAXS" in summary


def test_SchedulingServer_credentials():
    ss = IS_SchedulingServer(dev=True)  # prepare to connect
    assert ss is not None
    assert "-dev" in ss.base

    # no credentials
    with pytest.raises(IS_MissingAuthentication) as reason:
        ss.webget("run/getAllRuns")
    assert "Authentication is not set." in str(reason)

    if not is_aps_workstation():
        return

    # These tests only work at APS

    # empty credentials
    ss.creds = ("", "")
    with pytest.raises(IS_Unauthorized) as reason:
        ss.webget("run/getAllRuns")
    assert "401: Unauthorized" in str(reason)

    # credentials not recognized
    ss.creds = ("username", "password")
    with pytest.raises(IS_Unauthorized) as reason:
        ss.webget("run/getAllRuns")
    assert "401: Unauthorized" in str(reason)

    # valid credentials from file
    if CREDS_FILE.exists():
        # Tests only work at APS with valid credentials
        ss.auth_from_file(CREDS_FILE)
        with does_not_raise() as reason:
            reply = ss.webget("run/getAllRuns")
        assert reply is not None

        # Move this assertion to tests of exceptions
        with pytest.raises(IS_Exception) as reason:
            ss.runsByDateTime(2024)  # should use iso8601 text or None
        # The text "Unparseable date" might be converted into "..."
        assert "Internal Server Error" in str(reason)


def test_SchedulingServer():
    ss = IS_SchedulingServer(dev=True)  # prepare to connect
    assert ss is not None
    if not CREDS_FILE.exists() or not is_aps_workstation():
        return  # Can't test anything here.

    ss.auth_from_file(CREDS_FILE)
    assert len(ss.runs) > 40  # more than 40 run cycles in the database

    run = ss.current_run
    assert isinstance(run, dict)

    run = run["runName"]
    assert isinstance(run, str)
    assert "-" in run
    # this test might fail during year-end shutdown
    # assert run.split("-")[0] == str(datetime.datetime.now().year)
    calendar_year = datetime.datetime.now().year
    run_year = int(run.split("-")[0])
    assert abs(calendar_year - run_year) in (0, 1)

    assert len(ss.runsByRunYear(2023)) == 3
    assert len(ss.runsByRunYear(2024)) == 2  # APS-U shutdown

    assert len(ss.runsByDateTime("2024-11-15T12:41:56-06:00")) == 1

    assert 30 < len(ss.activeBeamlines) < 200


@pytest.mark.parametrize(
    "beamline, run, expected",
    [
        ["8-ID-E", "2024-3", 0],
        ["8-ID-I", "2024-3", 0],
        ["12-ID-E", "2024-3", 0],
        ["1-ID-B,C,E", None, 666],  # Not authorized
    ],
)
def test_beamlines(beamline, run, expected):
    ss = IS_SchedulingServer(dev=True)  # prepare to connect
    assert ss is not None
    if not CREDS_FILE.exists() or not is_aps_workstation():
        return  # Can't test anything here.

    ss.auth_from_file(CREDS_FILE)
    assert len(ss.runs) > 40  # more than 40 run cycles in the database

    assert beamline in ss.beamlines

    my_beamlines = [entry["beamline"] for entry in ss.authorizedBeamlines]
    if beamline in my_beamlines:
        # expected = 0  # expect to see zero requests when unauthorized
        requests = ss.proposals(beamline, run)
        assert len(requests) == expected
    else:
        with pytest.raises(IS_NotAllowedToRespond) as reason:
            ss.proposals(beamline, run)
        # text truncated: "User not authorized for beamline Id :"
        assert "Forbidden" in str(reason)