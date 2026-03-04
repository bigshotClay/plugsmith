"""Tests for plugsmith.runner (SubprocessRunner)."""

import pytest


def test_import():
    """SubprocessRunner is importable without a running Textual app."""
    from plugsmith.runner import SubprocessRunner
    assert SubprocessRunner is not None


def test_message_types():
    from plugsmith.runner import SubprocessRunner
    line = SubprocessRunner.OutputLine("hello", is_stderr=False)
    assert line.line == "hello"
    assert not line.is_stderr

    err_line = SubprocessRunner.OutputLine("oops", is_stderr=True)
    assert err_line.is_stderr

    started = SubprocessRunner.ProcessStarted(["dmrconf", "detect"])
    assert started.cmd == ["dmrconf", "detect"]

    finished = SubprocessRunner.ProcessFinished(0, ["dmrconf", "detect"])
    assert finished.returncode == 0
