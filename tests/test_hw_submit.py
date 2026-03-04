"""Unit tests for plugsmith.hw_submit."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests

import plugsmith.hw_submit as hw_submit
from plugsmith.hw_submit import is_submission_needed, submit_hw_profile


# ---------------------------------------------------------------------------
# is_submission_needed
# ---------------------------------------------------------------------------

def test_known_model_not_needed():
    """Supported radio → never needs submission."""
    assert is_submission_needed("d878uv2", "") is False


def test_known_model_with_firmware_not_needed():
    assert is_submission_needed("d878uv2", "3.06") is False


def test_unknown_model_no_firmware_needed():
    """Unsupported radio with no prior submission → needs it."""
    assert is_submission_needed("unknownkey", "") is True


def test_unknown_model_firmware_set_not_needed():
    """Unsupported radio but firmware already submitted → skip."""
    assert is_submission_needed("unknownkey", "3.06") is False


# ---------------------------------------------------------------------------
# submit_hw_profile — empty token guard
# ---------------------------------------------------------------------------

def test_empty_token_raises_runtime_error():
    """No token → RuntimeError before any network call."""
    original = hw_submit.GITHUB_ISSUES_TOKEN
    hw_submit.GITHUB_ISSUES_TOKEN = ""
    try:
        with patch("plugsmith.hw_submit.requests.post") as mock_post:
            with pytest.raises(RuntimeError, match="GITHUB_ISSUES_TOKEN"):
                submit_hw_profile(
                    radio_key="unknownkey",
                    display_name="Unknown Radio",
                    firmware_version="1.00",
                    hw_settings_yaml="",
                    notes="",
                    dmrconf_version="v0.11.0",
                )
            mock_post.assert_not_called()
    finally:
        hw_submit.GITHUB_ISSUES_TOKEN = original


# ---------------------------------------------------------------------------
# submit_hw_profile — happy path
# ---------------------------------------------------------------------------

def _mock_response(url: str = "https://github.com/test/issue/1") -> MagicMock:
    resp = MagicMock()
    resp.json.return_value = {"html_url": url}
    resp.raise_for_status.return_value = None
    return resp


def test_submit_calls_correct_endpoint():
    hw_submit.GITHUB_ISSUES_TOKEN = "test-token"
    try:
        with patch("plugsmith.hw_submit.requests.post", return_value=_mock_response()) as mock_post:
            submit_hw_profile("unknownkey", "Unknown", "2.00", "", "", "v0.11.0")
        called_url = mock_post.call_args[0][0]
        assert called_url == hw_submit._ISSUES_URL
    finally:
        hw_submit.GITHUB_ISSUES_TOKEN = ""


def test_submit_title_contains_firmware_and_radio():
    hw_submit.GITHUB_ISSUES_TOKEN = "test-token"
    try:
        with patch("plugsmith.hw_submit.requests.post", return_value=_mock_response()) as mock_post:
            submit_hw_profile("unknownkey", "Unknown Radio", "3.06", "", "", "v0.11.0")
        payload = mock_post.call_args.kwargs["json"]
        assert "3.06" in payload["title"]
        assert "Unknown Radio" in payload["title"]
    finally:
        hw_submit.GITHUB_ISSUES_TOKEN = ""


def test_submit_body_contains_expected_fields():
    hw_submit.GITHUB_ISSUES_TOKEN = "test-token"
    try:
        with patch("plugsmith.hw_submit.requests.post", return_value=_mock_response()) as mock_post:
            submit_hw_profile(
                radio_key="unknownkey",
                display_name="Unknown Radio",
                firmware_version="3.06",
                hw_settings_yaml="power: high",
                notes="Works great",
                dmrconf_version="v0.11.0",
            )
        payload = mock_post.call_args.kwargs["json"]
        body = payload["body"]
        assert "unknownkey" in body
        assert "3.06" in body
        assert "power: high" in body
        assert "Works great" in body
        assert "v0.11.0" in body
    finally:
        hw_submit.GITHUB_ISSUES_TOKEN = ""


def test_submit_authorization_header_uses_bearer():
    hw_submit.GITHUB_ISSUES_TOKEN = "my-secret-token"
    try:
        with patch("plugsmith.hw_submit.requests.post", return_value=_mock_response()) as mock_post:
            submit_hw_profile("unknownkey", "Unknown", "1.00", "", "", "v0.11.0")
        headers = mock_post.call_args.kwargs["headers"]
        assert headers["Authorization"] == "Bearer my-secret-token"
    finally:
        hw_submit.GITHUB_ISSUES_TOKEN = ""


def test_submit_returns_html_url():
    hw_submit.GITHUB_ISSUES_TOKEN = "test-token"
    expected = "https://github.com/org/repo/issues/42"
    try:
        with patch("plugsmith.hw_submit.requests.post", return_value=_mock_response(expected)):
            url = submit_hw_profile("unknownkey", "Unknown", "1.00", "", "", "v0.11.0")
        assert url == expected
    finally:
        hw_submit.GITHUB_ISSUES_TOKEN = ""


def test_submit_http_error_propagates():
    hw_submit.GITHUB_ISSUES_TOKEN = "test-token"
    try:
        resp = MagicMock()
        resp.raise_for_status.side_effect = requests.HTTPError("403 Forbidden")
        with patch("plugsmith.hw_submit.requests.post", return_value=resp):
            with pytest.raises(requests.HTTPError):
                submit_hw_profile("unknownkey", "Unknown", "1.00", "", "", "v0.11.0")
    finally:
        hw_submit.GITHUB_ISSUES_TOKEN = ""


# ---------------------------------------------------------------------------
# Body "(none)" fallback when fields are empty
# ---------------------------------------------------------------------------

def test_body_shows_none_when_hw_yaml_empty():
    hw_submit.GITHUB_ISSUES_TOKEN = "test-token"
    try:
        with patch("plugsmith.hw_submit.requests.post", return_value=_mock_response()) as mock_post:
            submit_hw_profile("unknownkey", "Unknown", "1.00", "", "", "v0.11.0")
        body = mock_post.call_args.kwargs["json"]["body"]
        assert "(none" in body  # matches "(none)" or "(none — ...)"
    finally:
        hw_submit.GITHUB_ISSUES_TOKEN = ""


def test_body_shows_none_when_notes_empty():
    hw_submit.GITHUB_ISSUES_TOKEN = "test-token"
    try:
        with patch("plugsmith.hw_submit.requests.post", return_value=_mock_response()) as mock_post:
            submit_hw_profile("unknownkey", "Unknown", "1.00", "power: high", "", "v0.11.0")
        body = mock_post.call_args.kwargs["json"]["body"]
        assert "(none)" in body
    finally:
        hw_submit.GITHUB_ISSUES_TOKEN = ""
