"""Test module apsbss_ophyd."""

import datetime
import time

import pyRestTable

from ..apsbss import connect_epics
from ._core import BSS_TEST_IOC_PREFIX
from ._core import wait_for_IOC


def test_EpicsBssDevice(ioc):
    ioc.bss = connect_epics(BSS_TEST_IOC_PREFIX)
    assert ioc.bss is not None

    for cpt in "esaf proposal ioc_host ioc_user status_msg".split():
        assert cpt in ioc.bss.component_names

    ioc.bss.wait_for_connection(timeout=5)
    assert ioc.bss.connected

    ioc.bss.status_msg.put("")
    wait_for_IOC()
    assert ioc.bss.status_msg.get(use_monitor=False) == ""

    ioc.bss.status_msg.put("this is a test")
    time.sleep(0.1)
    assert ioc.bss.status_msg.get(use_monitor=False) == "this is a test"

    ioc.bss.clear()
    wait_for_IOC()
    assert ioc.bss.status_msg.get(use_monitor=False) == "Cleared"

    table = ioc.bss._table()
    assert isinstance(table, pyRestTable.Table)
    assert len(table.labels) == 3
    assert len(table.rows) >= 137
    assert len(table.rows[0]) == 3
    assert table.rows[0][0] == f"{BSS_TEST_IOC_PREFIX}esaf:description"
    assert table.rows[0][1] == ""
    assert isinstance(table.rows[0][2], (datetime.datetime, str))

    assert table.rows[-1][0] == f"{BSS_TEST_IOC_PREFIX}status"
    assert table.rows[-1][1] == "Cleared"
    assert isinstance(table.rows[-1][2], (datetime.datetime, str))
