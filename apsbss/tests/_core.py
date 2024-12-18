"""Common support for testing."""

import pathlib
import time
import uuid

import yaml

BSS_TEST_IOC_PREFIX = f"tst{uuid.uuid4().hex[:7]}:bss:"
SRC_PATH = pathlib.Path(__file__).parent.parent
TEST_DATA_PATH = pathlib.Path(__file__).parent / "data"
CREDS_FILE = TEST_DATA_PATH / "dev_creds.txt"


def wait_for_IOC(delay=0.05):
    """Short delay for EPICS IOC processing."""
    time.sleep(delay)


def yaml_loader(file):
    """Load content from a YAML file."""
    return yaml.load(open(file).read(), Loader=yaml.SafeLoader)
