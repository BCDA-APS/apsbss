import pytest

from .. import apsbss
from ..core import is_xsd_workstation
from ..server_interface import RunNotFound


def test_run_not_found():
    if is_xsd_workstation():
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
        [["2020-2"], 9, 38],
        [("2020-1", "2020-2"), 9, 41 + 38],
    ],
)
def test_esafs(run, sector, count):
    if is_xsd_workstation():
        if not isinstance(run, str):
            with pytest.raises(TypeError) as reason:
                apsbss.server.esafs(sector, run)
            assert "Not a string: run=" in str(reason)
        else:
            assert len(apsbss.server.esafs(sector, run)) == count


@pytest.mark.parametrize(
    "run, bl, count",
    [
        ["2011-3", "9-ID-B,C", 10],
        ["2020-1", "9-ID-B,C", 12],
        ["2020-2", "9-ID-B,C", 21],
        [("2020-2"), "9-ID-B,C", 21],
        [["2020-1", "2020-2"], "9-ID-B,C", 12 + 21],
    ],
)
def test_proposals(run, bl, count):
    if is_xsd_workstation():
        if not isinstance(run, str):
            with pytest.raises(TypeError) as reason:
                apsbss.server.proposals(bl, run)
            assert "Not a string: run=" in str(reason)
        else:
            assert len(apsbss.server.proposals(bl, run)) == count
