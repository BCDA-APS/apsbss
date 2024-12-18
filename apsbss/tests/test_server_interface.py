"""Test the servers module."""

from contextlib import nullcontext as does_not_raise

import pytest

from ..core import is_xsd_workstation
from ..server_interface import EsafNotFound
from ..server_interface import ProposalNotFound
from ..server_interface import RunNotFound
from ..server_interface import Server
from ..server_interface import ServerException


def test_Server():
    server = Server()
    assert server is not None

    if not is_xsd_workstation():
        return

    assert 10 < len(server.beamlines) < 100
    assert "2-BM-A,B" in server.beamlines
    assert len(server.current_run) == 6
    assert 10 < len(server.runs) < 100
    assert "2024-3" in server.runs


def test_Server_esaf():
    server = Server()

    if not is_xsd_workstation():
        return

    esaf = server.esaf(251426)  # , 8, "2022-1")
    assert esaf is not None
    assert isinstance(esaf, dict)
    # 'esafId', 'description', 'sector', 'esafTitle',
    # 'experimentStartDate', 'experimentEndDate', 'esafStatus', 'experimentUsers'
    assert esaf["experimentStartDate"] == "2022-02-01 08:00:00"
    assert esaf["experimentEndDate"] == "2022-04-28 08:00:00"
    assert "Align and characterize 8-ID-E experim" in esaf["esafTitle"]
    assert "Align x-ray optical components" in esaf["description"]


def test_Server_proposal():
    server = Server()

    if not is_xsd_workstation():
        return

    proposal = server.proposal(78243, "8-ID-I", "2022-1")
    assert proposal is not None
    assert not isinstance(proposal, dict)
    assert hasattr(proposal, "__dict__")
    assert hasattr(proposal, "title")
    assert "dynamics of colloidal suspensions" in proposal.title


def test_esaf_table():
    server = Server()

    if not is_xsd_workstation():
        return

    table = server.esaf_table(server.esafs(12, "2024-3"))
    assert len(table.rows) >= 23
    rowNum = -1
    assert len(table.rows[rowNum]) == 7
    assert table.rows[rowNum][0] == 275724
    assert table.rows[rowNum][1] == "Approved"
    assert table.rows[rowNum][2] == "2024-3"
    assert table.rows[rowNum][3] == "2024-10-08"
    assert table.rows[rowNum][4] == "2024-12-19"
    assert table.rows[rowNum][-1] == "12-ID Operations Commissioning"


@pytest.mark.parametrize(
    "arg, expected",
    [
        [None, "current"],
        ["", "current"],
        ["current", "current"],
        ["now", "current"],
        ["past", "prior"],
        ["previous", "prior"],
        ["prior", "prior"],
        ["future", "next"],
        ["next", "next"],
        ["all", "all"],
        ["recent", "recent"],
    ],
)
def test_parse_runs_arg(arg, expected):
    server = Server()

    if not is_xsd_workstation():
        return

    if expected == "current":
        expected = {server.current_run}
    elif expected == "prior":
        rr = sorted(server.runs, reverse=True)
        runs = rr[1 + rr.index(server.current_run)]
        expected = {runs}
    elif expected == "next":
        rr = sorted(server.runs, reverse=True)
        p = rr.index(server.current_run)
        if p == 0:
            raise KeyError(f"No runs in the future for run={server.current_run}.")
        runs = rr[p - 1]
        expected = {runs}
    elif expected == "all":
        expected = set(server.runs)
    elif expected == "recent":
        expected = set(server.recent_runs())
    assert server.parse_runs_arg(arg) == expected


def test_proposal_table():
    server = Server()

    if not is_xsd_workstation():
        return

    table = server.proposal_table(server.proposals("12-ID-B", "2024-3"))
    assert len(table.rows) == 2
    assert len(table.rows[0]) == 6
    assert table.rows[0][0] == 1008087
    assert table.rows[0][1] == "2024-3"
    assert table.rows[0][2] == "2024-12-11"
    assert table.rows[0][3] == "2024-12-14"
    assert table.rows[0][-1] == "Studying biological interactions in b..."


@pytest.mark.parametrize(
    "method, args, context, text",
    [
        ["esafs", (8, "1915-1"), RunNotFound, "Could not find run='1915-1'"],
        ["esaf", ["1"], ServerException, "esaf_id='1'"],
        ["esaf", ["1"], EsafNotFound, "esaf_id='1'"],
        [
            "proposal",
            (1, "8-ID-I", "2024-3"),
            ProposalNotFound,
            "proposal_id=1 beamline='8-ID-I' run='2024-3'",
        ],
    ],
)
def test_Server_raises(method, args, context, text):
    server = Server()

    if not is_xsd_workstation():
        return

    with pytest.raises(context) as reason:
        getattr(server, method)(*args)
    assert text in str(reason)


@pytest.mark.parametrize(
    "method, arg, kwargs",
    [
        ["current_esafs", 8, {}],
        ["current_esafs_and_proposals", "8-ID-E,I", {}],
        ["current_proposals", "8-ID-E,I", {}],
    ],
)
def test_Server_not_raises(method, arg, kwargs):
    server = Server()

    if not is_xsd_workstation():
        return

    with does_not_raise():
        getattr(server, method)(arg, **kwargs)
