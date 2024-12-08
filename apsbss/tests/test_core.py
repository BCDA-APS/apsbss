"""Test the core module."""

import datetime
from contextlib import nullcontext as does_not_raise

import pytest

from ..core import ProposalBase
from ..core import ScheduleInterfaceBase
from ..core import User
from ..core import miner
from ._core import TEST_DATA_PATH
from ._core import yaml_loader

nested = yaml_loader(TEST_DATA_PATH / "is-gupId-77056.yml")
minimal_proposal_dict = {
    "id": 123456,
    "title": "test proposal",
    "startTime": str(datetime.datetime.now().astimezone()),
    "endTime": str(datetime.datetime.now().astimezone()),
    "experimenters": [],
}


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


@pytest.mark.parametrize(
    "path, exception, text",
    [
        ["proposal.experimenters.badge", AttributeError, "'list' object has no attribute 'get'"],
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
    prop = ProposalBase({})
    assert prop.to_dict() == {}
    with pytest.raises(KeyError) as reason:
        prop.proposal_id
    assert "id" in str(reason)

    prop = ProposalBase(minimal_proposal_dict)
    assert prop.to_dict() == minimal_proposal_dict
    assert prop.proposal_id == 123456
    assert prop.title == "test proposal"
    assert not prop.current

    # set the end time into the future so this proposal is current
    minimal_proposal_dict["endTime"] = "2100-01-02 01:02-06:00"
    prop = ProposalBase(minimal_proposal_dict)
    assert prop.current


def test_ScheduleInterfaceBase():
    with pytest.raises(TypeError) as reason:
        ScheduleInterfaceBase()
    assert "Can't instantiate abstract class" in str(reason)
    assert "with abstract methods" in str(reason)

    class MinimalSubClass(ScheduleInterfaceBase):
        @property
        def beamlines(self):
            return []

        def proposals(self, beamline, run):
            return {}

        @property
        def runs(self):
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