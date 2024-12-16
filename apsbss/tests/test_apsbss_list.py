import sys

import pytest

from ..apsbss import main
from ..core import is_xsd_workstation
from ..server_interface import RunNotFound
from ..server_interface import Server


def test_myoutput(capsys):  # or use "capfd" for fd-level
    """Example test capturing stdout and stderr for testing."""
    print("hello")
    sys.stderr.write("world\n")
    out, err = capsys.readouterr()
    assert out == "hello\n"
    assert err == "world\n"
    print("next")
    out, err = capsys.readouterr()
    assert out.strip() == "next"
    assert err.strip() == ""


def test_no_run_given(capsys):
    if is_xsd_workstation():
        sys.argv = [
            sys.argv[0],
            "list",
            "12-ID-B",
        ]
        main()
        out, err = capsys.readouterr()
        ss = Server()
        assert isinstance(ss.bss_api._runs, list)
        assert isinstance(ss._runs, dict)
        assert ss.current_run in str(out)
        assert err.strip() == ""


# VERY slow test
# def test_run_all(capsys):
#     if is_xsd_workstation():
#         sys.argv = [
#             sys.argv[0],
#             "list",
#             "9-ID-B,C",
#             "--run",
#             "all",
#         ]
#         main()
#         out, err = capsys.readouterr()
#         assert "2020-1" in str(out)
#         assert err.strip() == ""


def test_run_future(capsys):
    if is_xsd_workstation():
        sys.argv = [
            sys.argv[0],
            "list",
            "8-ID-E,I",
            "--run",
            "future",
        ]
        main()
        out, err = capsys.readouterr()
        assert "status" in str(out)
        assert err.strip() == ""


def test_run_blank(capsys):
    if is_xsd_workstation():
        sys.argv = [
            sys.argv[0],
            "list",
            "8-ID-E",
            "--run",
            "",
        ]
        main()
        out, err = capsys.readouterr()
        ss = Server()
        assert ss.current_run in str(out)
        assert err.strip() == ""


def test_run_by_name(capsys):
    if is_xsd_workstation():
        sys.argv = [
            sys.argv[0],
            "list",
            "9-ID-B,C",
            "--run",
            "2020-2",
        ]
        main()
        out, err = capsys.readouterr()
        assert "2020-2" in str(out)
        assert err.strip() == ""


def test_run_now(capsys):
    if is_xsd_workstation():
        sys.argv = [
            sys.argv[0],
            "list",
            "8-ID-I",
            "--run",
            "now",
        ]
        main()
        out, err = capsys.readouterr()
        ss = Server()
        assert ss.current_run in str(out)
        assert err.strip() == ""


def test_run_not_found():
    if is_xsd_workstation():
        sys.argv = [
            sys.argv[0],
            "list",
            "9-ID-B,C",
            "--run",
            "not-a-run",
        ]
        with pytest.raises(RunNotFound) as exc:
            main()
        assert "Could not find run=" in str(exc.value)


def test_run_previous(capsys):
    if is_xsd_workstation():
        for when in "past previous prior".split():
            sys.argv = [
                sys.argv[0],
                "list",
                "9-ID-B,C",
                "--run",
                when,
            ]
            main()
            out, err = capsys.readouterr()
            assert "Approved" in str(out)
            assert err.strip() == ""


# def test_run_recent(capsys):
#     if is_xsd_workstation():
#         sys.argv = [
#             sys.argv[0],
#             "list",
#             "8-ID-I",
#             "--run",
#             "recent",
#         ]
#         main()
#         out, err = capsys.readouterr()
#         assert "status" in str(out)
#         assert err.strip() == ""
