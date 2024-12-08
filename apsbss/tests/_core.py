"""Common support for testing."""

import socket
import pathlib
import yaml

TEST_DATA_PATH = pathlib.Path(__file__).parent / "data"
CREDS_FILE = TEST_DATA_PATH / "dev_creds.txt"


def is_aps_workstation():
    return socket.getfqdn().endswith(".aps.anl.gov")


def yaml_loader(file):
    return yaml.load(open(file).read(), Loader=yaml.SafeLoader)
