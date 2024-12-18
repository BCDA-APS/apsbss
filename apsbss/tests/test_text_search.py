"""Test module: text_search"""

import pytest

from ..bss_dm import DM_BeamtimeProposal
from ..bss_is import IS_BeamtimeRequest
from ..core import Esaf
from ..text_search import SearchEngine
from ._core import TEST_DATA_PATH
from ._core import yaml_loader

TEST_FILES = [
    TEST_DATA_PATH / nm
    for nm in """
        dm-btr-64057.yml
        dm-btr-77056.yml
        dm-btr-78243.yml
        dm-btr-78544.yml
        dm-esaf-226319.yml
        is-activity-78544.yml
        is-btr-77056.yml
        is-btr-78544.yml
        user.yml
        dev_creds.txt
        """.split()
]


@pytest.fixture
def engine():
    """Read from the test data files."""
    esafs, props = [], []
    for fname in TEST_FILES:
        if not fname.name.endswith(".yml"):
            continue
        content = yaml_loader(fname)
        if fname.name.startswith("dm-esaf"):
            esafs.append(Esaf(content, "test"))
        elif fname.name.startswith("dm-btr"):
            props.append(DM_BeamtimeProposal(content, "test"))
        elif fname.name.startswith("is-btr"):
            props.append(IS_BeamtimeRequest(content, "test"))

    assert len(esafs) == 1
    assert len(props) == 6

    engine = SearchEngine()
    assert engine is not None

    engine.index_esafs(esafs)
    engine.index_proposals(props)

    hits = engine.search("ESAF", default_key="type")
    assert len(hits) == len(esafs)

    hits = engine.search("type:proposal")
    assert len(hits) == len(props)

    yield engine


@pytest.mark.parametrize(
    "query, n_matches",
    [
        ["pi:Andrew", 2],
        ["pi:Andrew run:test", 1],
        ["pi:Andrew run:'2022-2'", 1],
        ["title:*axs", 3],
        ["title:(Commission *axs)", 1],
        ["'partner user'", 1],
    ],
)
def test(query, n_matches, engine):
    """docs"""
    hits = engine.search(query)
    assert len(hits) == n_matches
