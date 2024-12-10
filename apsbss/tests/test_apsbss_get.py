import pytest

from .. import apsbss
from ..servers import RunNotFound
from ._core import is_aps_workstation


def test_run_not_found():
    if is_aps_workstation():
        run = "sdfsdjfyg"
        with pytest.raises(RunNotFound) as exc:
            apsbss.server.esafs(9, run)
        assert f"Could not find {run=!r}" in str(exc.value)

        run = "not-a-run"
        with pytest.raises(RunNotFound) as exc:
            apsbss.server.esafs(9, run)
        assert f"Could not find {run=!r}" in str(exc.value)


@pytest.mark.parametrize(
    "run, sector, count",
    [
        ["2011-3", 9, 33],
        ["2020-1", 9, 41],
        ["2020-2", 9, 38],
        [("2020-2"), 9, 38],
        # [["2020-1", "2020-2"], 9, 41+38],  # TODO re-enable
    ]
)
def test_esafs(run, sector, count):
    if is_aps_workstation():
        assert len(apsbss.server.esafs(sector, run)) == count


@pytest.mark.parametrize(
    "run, bl, count",
    [
        ["2011-3", "9-ID-B,C", 10],
        ["2020-1", "9-ID-B,C", 12],
        ["2020-2", "9-ID-B,C", 21],
        [("2020-2"), "9-ID-B,C", 21],
        # [["2020-1", "2020-2"], "9-ID-B,C", 12+21],  # TODO re-enable
    ]
)
def test_proposals(run, bl, count):
    if is_aps_workstation():
        assert len(apsbss.server.proposals(bl, run)) == count
