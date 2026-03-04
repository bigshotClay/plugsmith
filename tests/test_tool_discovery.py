"""Tests for plugsmith.tool_discovery."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from plugsmith.tool_discovery import find_dmrconf, list_radio_models, ToolStatus


def test_find_dmrconf_not_on_path():
    with patch("shutil.which", return_value=None):
        status = find_dmrconf()
    assert not status.found
    assert "PATH" in (status.error or "")


def test_find_dmrconf_found(tmp_path):
    fake_binary = tmp_path / "dmrconf"
    fake_binary.write_text("#!/bin/sh\necho 'dmrconf 0.12.0'")
    fake_binary.chmod(0o755)

    import subprocess
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
