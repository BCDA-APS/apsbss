"""Test the core module."""

import datetime
from contextlib import nullcontext as does_not_raise

import pytest

from ..core import DM_APS_DB_WEB_SERVICE_URL
from ..core import ProposalBase
from ..core import ScheduleInterfaceBase
from ..core import User
from ..core import iso2dt
from ..core import miner
from ..core import printColumns
from ..core import trim
from ._core import TEST_DATA_PATH
from ._core import yaml_loader

nested = yaml_loader(TEST_DATA_PATH / "is-btr-77056.yml")
minimal_proposal_dict = {
    "id": 123456,
    "title": "test proposal",
    "startTime": str(datetime.datetime.now().astimezone()),
    "endTime": str(datetime.datetime.now().astimezone()),
    "experimenters": [],
}


def test_url():
    url = "https://xraydtn01.xray.aps.anl.gov:11336"
    assert DM_APS_DB_WEB_SERVICE_URL == url


def test_iso2dt():
    dt = datetime.datetime(2020, 6, 30, 12, 31, 45, 67890).astimezone()
    assert iso2dt("2020-06-30 12:31:45.067890") == dt


@pytest.mark.parametrize(
    "path, default, expected",
    [
        ["beamline.sector.sectorName", None, "Sector 9"],
        ["beamlineId", None, "9-ID-B,C"],
        ["beamtime.beamlineFirst.sector.sectorId", None, 9],
    ],
)
def test_miner(path, default, expected):
    result = miner(nested, path, default)
    assert result == expected, f"{path=!r} {default=!r} {expected=!r} {result=!r}"


def test_printColumns(capsys):
    printColumns("1 2 3 4 5 6".split(), numColumns=3, width=3)
    captured = capsys.readouterr()
    received = captured.out.strip().split("\n")
    assert len(received) == 2
    assert received[0].strip() == "1  3  5"
    assert received[1].strip() == "2  4  6"


def test_trim():
    source = "0123456789"
    assert trim(source) == source
    got = trim(source, length=8)
    assert got != source
    assert got.endswith("...")
    assert len(got) == 8
    assert got == "01234..."


@pytest.mark.parametrize(
    "path, exception, text",
    [
        [
            "proposal.experimenters.badge",
            AttributeError,
            "'list' object has no attribute 'get'",
        ],
        ["does-not-exist", does_not_raise, "None"],
        ["beamtime.does-not-exist", does_not_raise, "None"],
    ],
)
def test_miner_raises(path, exception, text):
    if exception == does_not_raise:
        context = does_not_raise()
    else:
        context = pytest.raises(exception)
    with context as reason:
        miner(nested, path)
    assert text in str(reason)


def test_ProposalBase():
    prop = ProposalBase({}, "")
    assert prop.to_dict() == {}
    with pytest.raises(KeyError) as reason:
        _id = prop.proposal_id
    assert "id" in str(reason)

    prop = ProposalBase(minimal_proposal_dict, "")
    assert prop.to_dict() == minimal_proposal_dict
    assert prop.proposal_id == 123456
    assert prop.title == "test proposal"
    assert not prop.current

    # set the end time into the future so this proposal is current
    minimal_proposal_dict["endTime"] = "2100-01-02 01:02-06:00"
    prop = ProposalBase(minimal_proposal_dict, "")
    assert prop.current


def test_ScheduleInterfaceBase():
    with pytest.raises(TypeError) as reason:
        ScheduleInterfaceBase()
    assert "Can't instantiate abstract class" in str(reason)
    assert "abstract methods" in str(reason)

    class MinimalSubClass(ScheduleInterfaceBase):
        @property
        def beamlines(self):
            return []

        def proposals(self, beamline, run):
            return {}

        @property
        def _runs(self):
            return []

    sched = MinimalSubClass()
    assert sched is not None
    assert sched.beamlines == []
    assert sched.proposals(None, None) == {}
    assert sched.runs == []
    assert sched.current_run == {}
    assert sched.getProposal(123, None, None) is None


def test_User():
    user_data = yaml_loader(TEST_DATA_PATH / "user.yml")
    user = User(user_data)
    assert user is not None
    assert user.affiliation == "National Institute of Standards and Technology (NIST)"
    assert user.badge == "85849"
    assert user.email == "andrew.allen@nist.gov"
    assert user.firstName == "Andrew"
    assert user.is_pi
    assert user.lastName == "Allen"
    assert user.fullName == "Andrew Allen"
    assert str(user) == "Andrew Allen <andrew.allen@nist.gov>"
