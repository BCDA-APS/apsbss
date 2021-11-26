from .. import apsbss


def test_basic():
    assert apsbss.CONNECT_TIMEOUT == 5
    assert isinstance(apsbss._cache_, dict)
