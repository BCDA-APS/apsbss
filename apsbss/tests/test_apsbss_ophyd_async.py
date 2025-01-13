"""Test module apsbss_ophyd."""

import datetime

import pyRestTable

from ..apsbss_ophyd_async import EpicsBssDevice
from ._core import BSS_TEST_IOC_PREFIX


async def test_EpicsBssDevice(ioc):
    ioc.bss = EpicsBssDevice(prefix=BSS_TEST_IOC_PREFIX, name="bss")
    await ioc.bss.connect(mock=False)

    child_names = [name for name, child in ioc.bss.children()]
    for cpt in "esaf proposal ioc_host ioc_user status_msg".split():
        assert cpt in child_names

    await ioc.bss.status_msg.set("")
    assert (await ioc.bss.status_msg.get_value()) == ""

    await ioc.bss.status_msg.set("this is a test")
    assert (await ioc.bss.status_msg.get_value()) == "this is a test"

    await ioc.bss.clear()
    assert (await ioc.bss.status_msg.get_value()) == "Cleared"

    table = await ioc.bss._table()
    assert isinstance(table, pyRestTable.Table)
    assert len(table.labels) == 3
    assert len(table.rows) >= 137
    assert len(table.rows[0]) == 3
    assert table.rows[0][0] == f"ca://{BSS_TEST_IOC_PREFIX}esaf:description"
    assert table.rows[0][1] == ""
    assert isinstance(table.rows[0][2], (datetime.datetime, str))

    assert table.rows[-1][0] == f"ca://{BSS_TEST_IOC_PREFIX}status"
    assert table.rows[-1][1] == "Cleared"
    assert isinstance(table.rows[-1][2], (datetime.datetime, str))
