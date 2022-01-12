import pytest

from .. import apsbss
from ._core import is_aps_workstation


def test_cycle_not_found():
    if is_aps_workstation():
        cycle = "sdfsdjfyg"
        with pytest.raises(KeyError) as exc:
            apsbss.listESAFs(cycle, 9)
        assert f"APS cycle '{cycle}' not found." in str(exc.value)

        cycle = "not-a-cycle"
        with pytest.raises(KeyError) as exc:
            apsbss.listESAFs(cycle, 9)
        assert f"APS cycle '{cycle}' not found." in str(exc.value)


@pytest.mark.parametrize(
    "cycle, sector, count",
    [
        ["2011-3", 9, 33],
        ["2020-1", 9, 41],
        ["2020-2", 9, 38],
        [("2020-2"), 9, 38],
        [["2020-1", "2020-2"], 9, 41+38],
    ]
)
def test_listESAFs(cycle, sector, count):
    if is_aps_workstation():
        assert len(apsbss.listESAFs(cycle, sector)) == count


@pytest.mark.parametrize(
    "cycle, bl, count",
    [
        ["2011-3", "9-ID-B,C", 0],
        ["2020-1", "9-ID-B,C", 12],
        ["2020-2", "9-ID-B,C", 21],
        [("2020-2"), "9-ID-B,C", 21],
        [["2020-1", "2020-2"], "9-ID-B,C", 12+21],
    ]
)
def test_listProposals(cycle, bl, count):
    if is_aps_workstation():
        assert len(apsbss.listProposals(cycle, bl)) == count
