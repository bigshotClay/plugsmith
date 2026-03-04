"""Tests for plugsmith.tool_discovery."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from plugsmith.tool_discovery import (
    ToolStatus,
    builder_version,
    find_dmrconf,
    list_radio_models,
)


def test_find_dmrconf_not_on_path():
    with patch("shutil.which", return_value=None):
        status = find_dmrconf()
    assert not status.found
    assert "PATH" in (status.error or "")


def test_find_dmrconf_found(tmp_path):
    fake_binary = tmp_path / "dmrconf"
    fake_binary.write_text("#!/bin/sh\necho 'dmrconf 0.12.0'")
    fake_binary.chmod(0o755)

    mock_result = MagicMock()
    mock_result.stdout = "dmrconf 0.12.0\n"
    mock_result.stderr = ""

    with patch("shutil.which", return_value=str(fake_binary)):
        with patch("subprocess.run", return_value=mock_result):
            status = find_dmrconf()

    assert status.found
    assert status.version == "dmrconf 0.12.0"


def test_find_dmrconf_explicit_missing():
    status = find_dmrconf("/nonexistent/dmrconf")
    assert not status.found
    assert "not found" in (status.error or "").lower()


def test_find_dmrconf_explicit_found(tmp_path):
    """Explicit path that exists — covers line 80 (path = candidate)."""
    fake = tmp_path / "dmrconf"
    fake.write_text("#!/bin/sh")
    fake.chmod(0o755)

    mock_result = MagicMock()
    mock_result.stdout = "dmrconf 0.12.0\n"
    mock_result.stderr = ""

    with patch("subprocess.run", return_value=mock_result):
        status = find_dmrconf(str(fake))

    assert status.found
    assert status.path == fake


def test_find_dmrconf_subprocess_error(tmp_path):
    """subprocess raises OSError — covers except branch (lines 96-97)."""
    fake = tmp_path / "dmrconf"
    fake.write_text("#!/bin/sh")
    fake.chmod(0o755)

    with patch("subprocess.run", side_effect=OSError("exec failed")):
        status = find_dmrconf(str(fake))

    assert not status.found
    assert "exec failed" in (status.error or "")


def test_list_radio_models_fallback():
    """When dmrconf unavailable, should return fallback list."""
    with patch("subprocess.run", side_effect=FileNotFoundError):
        models = list_radio_models()
    assert len(models) > 0
    keys = [m[0] for m in models]
    assert "d878uv2" in keys


def test_list_radio_models_from_dmrconf():
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "d878uv2  AT-D878UVII (AnyTone)\nd868uv   AT-D868UV (AnyTone)\n"

    with patch("subprocess.run", return_value=mock_result):
        models = list_radio_models()

    assert ("d878uv2", "AT-D878UVII (AnyTone)") in models


def test_list_radio_models_skips_blank_and_comment_lines():
    """Blank lines and # comments are skipped — covers line 116 (continue)."""
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "\n# This is a comment\nd878uv2  AT-D878UVII (AnyTone)\n"

    with patch("subprocess.run", return_value=mock_result):
        models = list_radio_models()

    keys = [m[0] for m in models]
    assert "d878uv2" in keys
    assert not any(k.startswith("#") for k in keys)


def test_list_radio_models_single_word_line():
    """Line with only a key and no display name — covers lines 120-121."""
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "d878uv2\n"

    with patch("subprocess.run", return_value=mock_result):
        models = list_radio_models()

    assert ("d878uv2", "d878uv2") in models


def test_list_radio_models_with_explicit_path():
    """Passing dmrconf_path uses that binary — covers binary = dmrconf_path branch."""
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "d878uv2  Test Radio\n"

    with patch("subprocess.run", return_value=mock_result) as mock_run:
        list_radio_models(dmrconf_path="/custom/dmrconf")

    assert mock_run.call_args[0][0][0] == "/custom/dmrconf"


def test_builder_version_returns_string():
    """builder_version() returns a non-empty string — covers line 131."""
    version = builder_version()
    assert isinstance(version, str)
    assert "bundled" in version
