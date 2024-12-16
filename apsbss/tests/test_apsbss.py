"""
General tests of the apsbss module
"""

import sys
from contextlib import nullcontext as does_not_raise

import epics
import pytest
from ophyd.signal import EpicsSignalBase

from .. import apsbss
from .. import apsbss_makedb
from ..apsbss import connect_epics
from ..apsbss import epicsSetup
from ..core import is_xsd_workstation
from ..server_interface import Server
from ._core import BSS_TEST_IOC_PREFIX
from ._core import wait_for_IOC

# set default timeout for all EpicsSignal connections & communications
try:
    EpicsSignalBase.set_defaults(
        auto_monitor=True,
        timeout=60,
        write_timeout=60,
        connection_timeout=60,
    )
except RuntimeError:
    pass  # ignore if some EPICS object already created


@pytest.fixture(scope="function")
def argv():
    argv = [
        "apsbss",
    ]
    return argv


@pytest.fixture(scope="function")
def bss_PV():
    # try connecting with one of the PVs in the database
    run = epics.PV(f"{BSS_TEST_IOC_PREFIX}esaf:run")
    run.wait_for_connection(timeout=2)
    return run


def test_connect_epics(ioc):
    with does_not_raise():
        ioc.bss = connect_epics(BSS_TEST_IOC_PREFIX)
        assert ioc.bss.connected


def test_epics_setup_clear(ioc):
    with does_not_raise():
        ioc.bss = epicsSetup(BSS_TEST_IOC_PREFIX, "12-ID-B", run="2024-3")
        assert ioc.bss.connected

        wait_for_IOC()
        assert ioc.bss.status_msg.get(use_monitor=False) == "Done"


def test_general(capsys):
    assert 1 <= apsbss.CONNECT_TIMEOUT <= 10
    assert isinstance(apsbss.server, Server)

    sys.argv = [sys.argv[0], "--help"]
    with pytest.raises(SystemExit) as reason:
        apsbss.main()
    out, err = capsys.readouterr()
    assert "usage: " in out
    assert " [-h] [-v]" in out
    assert len(err) == 0
    assert "SystemExit(0)" in str(reason)


def test_not_at_aps():
    assert True  # test *something*
    if is_xsd_workstation():
        return


# do not try to test for fails using dm package, it has no timeout


def test_only_at_aps():
    assert True  # test *something*

    if not is_xsd_workstation():
        return

    runs = apsbss.server.runs
    assert len(runs) > 1
    assert apsbss.server.current_run in runs
    assert apsbss.server.runs[0] in runs
    assert len(apsbss.server.beamlines) > 1


def test_ioc(ioc, bss_PV):
    if not bss_PV.connected:
        assert True  # assert *something*
        return

    ioc.bss = connect_epics(BSS_TEST_IOC_PREFIX)
    ioc.bss.wait_for_connection(timeout=2)
    assert ioc.bss.connected
    assert ioc.bss.esaf.title.get(use_monitor=False) == ""
    assert ioc.bss.esaf.description.get(use_monitor=False) == ""


def test_EPICS(ioc, bss_PV):
    if not bss_PV.connected:
        assert True  # assert *something*
        return

    beamline = "12-BM-B"
    run = "2019-2"

    ioc.bss = apsbss.connect_epics(BSS_TEST_IOC_PREFIX)
    assert ioc.bss.connected
    assert ioc.bss.esaf.aps_run.get(use_monitor=False) == ""

    assert ioc.bss.esaf.aps_run.connected is True

    if not is_xsd_workstation():
        return

    # setup
    apsbss.epicsSetup(BSS_TEST_IOC_PREFIX, beamline, run)
    wait_for_IOC()

    assert ioc.bss.proposal.beamline_name.get(use_monitor=False) != "harpo"
    assert ioc.bss.proposal.beamline_name.get(use_monitor=False) == beamline
    assert ioc.bss.esaf.aps_run.get(use_monitor=False) == run
    assert ioc.bss.esaf.sector.get(use_monitor=False) == beamline.split("-")[0]

    # ESAF: 210443 XAFS summer school
    # GUP 64057 XAFS summar school
    esaf_id = "210443"
    proposal_id = 64057
    ioc.bss.esaf.aps_run.put("2019-2")
    ioc.bss.esaf.esaf_id.put(esaf_id)
    ioc.bss.proposal.proposal_id.put(str(proposal_id))
    apsbss.epicsUpdate(BSS_TEST_IOC_PREFIX)
    assert ioc.bss.esaf.title.get(use_monitor=False) == "APS/IIT EXAFS Summer School"
    assert ioc.bss.proposal.title.get(use_monitor=False) == "APS/IIT EXAFS Summer School"

    apsbss.epicsClear(BSS_TEST_IOC_PREFIX)
    assert ioc.bss.esaf.aps_run.get(use_monitor=False) != ""
    assert ioc.bss.esaf.title.get(use_monitor=False) == ""
    assert ioc.bss.proposal.title.get(use_monitor=False) == ""


def test_makedb(capsys):
    apsbss_makedb.main()
    db = capsys.readouterr().out.strip().split("\n")
    assert len(db) == 384
    random_spot_checks = {
        0: "#",
        1: "# file: apsbss.db",
        13: 'record(stringout, "$(P)status")',
        28: 'record(stringout, "$(P)esaf:id")',
        138: '    field(ONAM, "ON")',
        285: 'record(bo, "$(P)proposal:user5:piFlag") {',
    }
    for line_number, content in random_spot_checks.items():
        assert db[line_number] == content


def test_argv0(argv):
    sys.argv = argv
    assert len(sys.argv) == 1


def test_apsbss_commands_no_options(argv):
    sys.argv = argv
    args = apsbss.get_options()
    assert args is not None
    assert args.subcommand is None


def test_apsbss_commands_beamlines(argv, capsys):
    sys.argv = argv + ["beamlines"]
    args = apsbss.get_options()
    assert args is not None
    assert args.subcommand == sys.argv[1]

    if not is_xsd_workstation():
        return

    apsbss.main()
    out, err = capsys.readouterr()
    # test that report is beamline names, 4-columns
    assert len(err) == 0
    assert 1_000 < len(out) < 2_000
    assert 10 < len(out.split()) < 100
    assert "12-ID-B" in out.split()
    assert 10 < len(out.splitlines()) < 30
    assert len(out.splitlines()[0].split()) == 4


def test_apsbss_commands_esaf(argv):
    sys.argv = argv + ["esaf", "12345"]
    args = apsbss.get_options()
    assert args is not None
    assert args.subcommand == sys.argv[1]
    assert args.esafId == 12345


def test_apsbss_commands_proposal(argv):
    sys.argv = argv + [
        "proposal",
        "1",
        "1995-1",
        "my_beamline",
    ]
    args = apsbss.get_options()
    assert args is not None
    assert args.subcommand == sys.argv[1]
    assert args.proposalId == int(sys.argv[2])
    assert args.run == sys.argv[3]
    assert args.beamlineName == sys.argv[4]


def test_apsbss_commands_report(argv):
    sys.argv = argv + ["report", "IOC:prefix:"]
    args = apsbss.get_options()
    assert args is not None
    assert args.subcommand == sys.argv[1]
    assert args.prefix == "IOC:prefix:"


def test_apsbss_commands_runs(argv):
    sys.argv = argv + ["runs"]
    args = apsbss.get_options()
    assert args is not None
    assert args.subcommand == sys.argv[1]


def test_apsbss_commands_EPICS_clear(argv):
    sys.argv = argv + ["clear", "bss:"]
    args = apsbss.get_options()
    assert args is not None
    assert args.subcommand == sys.argv[1]
    assert args.prefix == sys.argv[2]


def test_apsbss_commands_EPICS_setup(argv):
    sys.argv = argv + ["setup", "bss:", "my_beamline", "1995-1"]
    args = apsbss.get_options()
    assert args is not None
    assert args.subcommand == sys.argv[1]
    assert args.prefix == sys.argv[2]
    assert args.beamlineName == sys.argv[3]
    assert args.run == sys.argv[4]


def test_apsbss_commands_EPICS_update(argv):
    sys.argv = argv + ["update", "bss:"]
    args = apsbss.get_options()
    assert args is not None
    assert args.subcommand == sys.argv[1]
    assert args.prefix == sys.argv[2]
