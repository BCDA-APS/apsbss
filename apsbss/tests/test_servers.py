"""Test the servers module."""

import pytest

from ..servers import EsafNotFound
from ..servers import ProposalNotFound
from ..servers import RunNotFound
from ..servers import Server
from ._core import is_aps_workstation


def test_Server():
    server = Server()
    assert server is not None
    
    if not is_aps_workstation():
        return

    assert 10 < len(server.beamlines) < 100
    assert len(server.current_run) == 6
    assert 10 < len(server.runs) < 100
    # TODO: more


    # proposal = server.get_proposal(78243, "8-ID-I", "2022-2")
    # assert proposal is not None
    # assert isinstance(proposal, dict)
    # assert "dynamics of colloidal suspensions" in proposal["title"]

    # TODO: test the other functions
    # getCurrentEsafs
    # getCurrentInfo
    # getCurrentProposals
    # getEsaf
    # getProposal
    # class DmRecordNotFound(Exception): ...
    # class EsafNotFound(DmRecordNotFound): ...
    # class ProposalNotFound(DmRecordNotFound): ...


def test_Server_raises():
    server = Server()
    
    if not is_aps_workstation():
        return

    with pytest.raises(RunNotFound) as reason:
        server.esafs(8, "1915-1")
    assert "Could not find run='1915-1'" in str(reason)

    with pytest.raises(EsafNotFound) as reason:
        server.esaf("1")
    assert "esaf_id='1'" in str(reason)

    with pytest.raises(ProposalNotFound) as reason:
        server.proposal(1, "8-ID-I", "2024-3")
    assert "proposal_id='1' beamline='8-ID-I' run='2024-3'" in str(reason)
