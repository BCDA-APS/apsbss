"""Test the Scheduling Server API (only works at APS)."""

import datetime
import pathlib
from contextlib import nullcontext as does_not_raise

import pytest

from ..sched_system import BeamtimeRequest
from ..sched_system import MissingAuthentication
from ..sched_system import NotAllowedToRespond
from ..sched_system import SchedulingServer
from ..sched_system import SchedulingServerException
from ..sched_system import Unauthorized
from ._core import is_aps_workstation

CREDS_FILE = pathlib.Path(__file__).parent / "dev_creds.txt"


def test_BeamtimeRequest():
    btr = BeamtimeRequest({})  # TODO: class needs to be filled out.
    assert btr.raw == {}
    assert not btr.current


def test_SchedulingServer_credentials():
    ss = SchedulingServer(dev=True)  # prepare to connect
    assert ss is not None
    assert "-dev" in ss.base

    # no credentials
    with pytest.raises(MissingAuthentication) as reason:
        ss.webget("run/getAllRuns")
    assert "Authentication is not set." in str(reason)

    if not is_aps_workstation():
        return

    # These tests only work at APS

    # empty credentials
    ss.creds = ("", "")
    with pytest.raises(Unauthorized) as reason:
        ss.webget("run/getAllRuns")
    assert "401: Unauthorized" in str(reason)

    # credentials not recognized
    ss.creds = ("username", "password")
    with pytest.raises(Unauthorized) as reason:
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
        with pytest.raises(SchedulingServerException) as reason:
            ss.runsByDateTime(2024)  # should use iso8601 text or None
        # The text "Unparseable date" might be converted into "..."
        assert "Internal Server Error" in str(reason)


def test_SchedulingServer():
    ss = SchedulingServer(dev=True)  # prepare to connect
    assert ss is not None
    if not CREDS_FILE.exists() or not is_aps_workstation():
        return  # Can't test anything here.

    ss.auth_from_file(CREDS_FILE)
    assert len(ss.allRuns) > 40  # more than 40 run cycles in the database

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
    ss = SchedulingServer(dev=True)  # prepare to connect
    assert ss is not None
    if not CREDS_FILE.exists() or not is_aps_workstation():
        return  # Can't test anything here.

    ss.auth_from_file(CREDS_FILE)
    assert len(ss.allRuns) > 40  # more than 40 run cycles in the database

    assert beamline in ss.beamlines

    my_beamlines = [entry["beamline"] for entry in ss.authorizedBeamlines]
    if beamline in my_beamlines:
        # expected = 0  # expect to see zero requests when unauthorized
        requests = ss.beamtime_requests(beamline, run)
        assert len(requests) == expected
    else:
        with pytest.raises(NotAllowedToRespond) as reason:
            ss.beamtime_requests(beamline, run)
        # text truncated: "User not authorized for beamline Id :"
        assert "Forbidden" in str(reason)
