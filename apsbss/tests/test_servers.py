"""Test the servers module."""

import pytest

from ..servers import Server
from ..servers import ProposalNotFound, RunNotFound, EsafNotFound


def test_Server():
    server = Server()
    assert server is not None
    assert 10 < len(server.beamlines) < 100
    assert len(server.current_run) == 6
    assert 10 < len(server.runs) < 100
    # TODO: more


def test_Server_raises():
    server = Server()

    with pytest.raises(RunNotFound) as reason:
        server.esafs(8, "1915-1")
    assert "Could not find run='1915-1'" in str(reason)

    with pytest.raises(EsafNotFound) as reason:
        server.get_esaf("1")
    assert "esaf_id='1'" in str(reason)

    with pytest.raises(ProposalNotFound) as reason:
        server.get_proposal(1, "8-ID-I", "2024-3")
    assert "proposal_id='1' beamline='8-ID-I' run='2024-3'" in str(reason)
