"""Test the DM Scheduling Server API (some tests only work at APS)."""

import datetime

from ..bss_dm import DM_BeamtimeProposal
from ..bss_dm import DM_ScheduleInterface
from ..core import Run
from ..core import User
from ..core import is_xsd_workstation
from ._core import TEST_DATA_PATH
from ._core import yaml_loader

DM_BTR_78243_FILE = TEST_DATA_PATH / "dm-btr-78243.yml"


def test_ApsDmScheduleInterface():
    ss = DM_ScheduleInterface()
    assert ss is not None

    if not is_xsd_workstation():
        return

    run = ss.current_run
    assert isinstance(run, Run)
    assert isinstance(run.startDate, datetime.datetime)
    assert isinstance(run.endDate, datetime.datetime)

    run = str(run)
    assert isinstance(run, str)
    assert "-" in run

    calendar_year = datetime.datetime.now().year
    run_year = int(run.split("-")[0])
    assert abs(calendar_year - run_year) in (0, 1)

    assert 30 < len(ss.beamlines) < 200


def test_DM_BeamtimeProposal():
    btr = DM_BeamtimeProposal({}, "")
    assert btr._raw == {}
    assert not btr.current

    btr = DM_BeamtimeProposal(yaml_loader(DM_BTR_78243_FILE), "2022-2")
    assert len(btr._raw) == 9
    assert not btr.current
    assert len(btr.users) == 9
    assert btr.pi == "Suresh Narayanan <sureshn@anl.gov>"
    assert "dynamics of colloidal suspensions" in btr.title
    assert isinstance(btr._users, list)
    assert isinstance(btr.users, list)

    user = btr.users[0]
    assert isinstance(user, str)
    assert user == "Qingteng Zhang"

    user = btr._users[0]
    assert isinstance(user, User)
    assert user.fullName == "Qingteng Zhang"
    assert user.firstName == "Qingteng"
    assert user.lastName == "Zhang"
    assert user.email == "qzhang234@anl.gov"
    assert str(user) == "Qingteng Zhang <qzhang234@anl.gov>"
    assert not user.is_pi
