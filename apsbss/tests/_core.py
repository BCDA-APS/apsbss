"""Common support for testing."""

import socket
import pathlib

TEST_DATA_PATH = pathlib.Path(__file__).parent / "data"
CREDS_FILE = TEST_DATA_PATH / "dev_creds.txt"


def is_aps_workstation():
    return socket.getfqdn().endswith(".aps.anl.gov")
