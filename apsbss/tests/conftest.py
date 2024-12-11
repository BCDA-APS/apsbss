"""Support for pytest."""

import subprocess
import time

import ophyd
import pytest

from ._core import BSS_TEST_IOC_PREFIX
from ._core import SRC_PATH

ophyd.set_cl("caproto")  # switch command layers

IOC_STARTUP_DELAY = 1.0  # seconds


class IOC_ProcessConfig:
    """Configuration of the EPICS IOC process."""

    bss = None
    manager = None
    ioc_name = "test_apsbss"
    ioc_prefix = None
    ioc_process = None

    def command(self, cmd):
        """doc"""
        return f"{self.manager} {cmd} {self.ioc_name} {self.ioc_prefix}"


def run_process(cmd):
    """Run a shell command."""
    return subprocess.Popen(
        cmd.encode().split(),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
    )


@pytest.fixture()
def ioc():
    """docs"""
    # set up
    cfg = IOC_ProcessConfig()

    cfg.manager = SRC_PATH / "apsbss_ioc.sh"
    cfg.ioc_prefix = BSS_TEST_IOC_PREFIX
    cfg.ioc_process = run_process(cfg.command("restart"))
    time.sleep(IOC_STARTUP_DELAY)  # allow the IOC to start

    # use
    yield cfg

    # tear down
    if cfg.bss is not None:
        cfg.bss.destroy()
        cfg.bss = None
    if cfg.ioc_process is not None:
        cfg.ioc_process = None
        run_process(cfg.command("stop"))
        cfg.manager = None
