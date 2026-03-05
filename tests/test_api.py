"""Tests for plugsmith.builder.api — RepeaterBookClient."""

from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

from plugsmith.builder.api import RepeaterBookClient, US_STATES


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_client(tmp_path, rate_limit: float = 0.0) -> RepeaterBookClient:
    return RepeaterBookClient(
        cache_dir=str(tmp_path / "cache"),
        rate_limit=rate_limit,
        user_agent="test/1.0 (test@example.com)",
    )


def _mock_response(data: list | dict, status: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = {"results": data} if isinstance(data, list) else data
    resp.raise_for_status.return_value = None
    return resp


# ---------------------------------------------------------------------------
# Constructor
# ---------------------------------------------------------------------------


class TestRepeaterBookClientConstructor:
    def test_raises_if_no_user_agent(self, tmp_path):
        client = RepeaterBookClient(cache_dir=str(tmp_path), user_agent="")
        with pytest.raises(ValueError, match="email"):
            client.fetch_state("MO")

    def test_creates_cache_dir(self, tmp_path):
        cache_dir = tmp_path / "newcache"
        assert not cache_dir.exists()
        _make_client(tmp_path)
        assert (tmp_path / "cache").exists()

    def test_sets_user_agent_header(self, tmp_path):
        client = _make_client(tmp_path)
        assert "test@example.com" in client.session.headers.get("User-Agent", "")


# ---------------------------------------------------------------------------
# fetch_state — unknown abbreviation
# ---------------------------------------------------------------------------


class TestFetchStateUnknown:
    def test_unknown_state_returns_empty(self, tmp_path):
        client = _make_client(tmp_path)
        result = client.fetch_state("ZZ")
        assert result == []


# ---------------------------------------------------------------------------
# fetch_state — cache hit
# ---------------------------------------------------------------------------


class TestFetchStateCacheHit:
    def test_returns_cached_data_without_http(self, tmp_path):
        client = _make_client(tmp_path)
        # Pre-populate cache for Missouri (state ID "29")
        cache_file = Path(client.cache_dir) / "state_29.json"
        cached = [{"Callsign": "W0MO", "Frequency": "146.520"}]
        cache_file.write_text(json.dumps(cached))
        # Make the cache appear fresh
        client.session.get = MagicMock()

        result = client.fetch_state("MO")
        assert result == cached
        client.session.get.assert_not_called()

    def test_calls_progress_callback_with_cached(self, tmp_path):
        calls = []
        client = RepeaterBookClient(
            cache_dir=str(tmp_path / "cache"),
            rate_limit=0.0,
            user_agent="test/1.0 (test@example.com)",
            progress_callback=lambda msg, cached: calls.append((msg, cached)),
        )
        cache_file = Path(client.cache_dir) / "state_29.json"
        cache_file.write_text(json.dumps([]))
        client.fetch_state("MO")
        assert any(cached is True for _, cached in calls)


# ---------------------------------------------------------------------------
# fetch_state — cache miss / live fetch
# ---------------------------------------------------------------------------


class TestFetchStateLive:
    def test_fetches_and_caches_data(self, tmp_path):
        client = _make_client(tmp_path)
        repeaters = [{"Callsign": "W0MO", "Frequency": "146.520"}]
        mock_resp = _mock_response(repeaters)
        client.session.get = MagicMock(return_value=mock_resp)

        result = client.fetch_state("MO")
        assert result == repeaters
        # Cache file should now exist
        cache_file = Path(client.cache_dir) / "state_29.json"
        assert cache_file.exists()
        assert json.loads(cache_file.read_text()) == repeaters

    def test_notifies_progress(self, tmp_path):
        calls = []
        client = RepeaterBookClient(
            cache_dir=str(tmp_path / "cache"),
            rate_limit=0.0,
            user_agent="test/1.0 (test@example.com)",
            progress_callback=lambda msg, cached: calls.append((msg, cached)),
        )
        # No cache file → live fetch
        mock_resp = _mock_response([])
        client.session.get = MagicMock(return_value=mock_resp)
        client.fetch_state("MO")
        assert any(cached is False for _, cached in calls)

    def test_notify_with_no_callback_uses_log(self, tmp_path):
        """_notify without callback should not raise."""
        client = _make_client(tmp_path)
        client._notify("test message")  # no progress_callback set

    def test_handles_401_raises_permission_error(self, tmp_path):
        client = _make_client(tmp_path)
        resp_401 = MagicMock()
        resp_401.status_code = 401
        resp_401.raise_for_status.return_value = None
        client.session.get = MagicMock(return_value=resp_401)
        with pytest.raises(PermissionError, match="401"):
            client.fetch_state("MO")

    def test_handles_429_rate_limit_retry(self, tmp_path):
        client = _make_client(tmp_path)
        repeaters = [{"Callsign": "W0MO"}]

        first = MagicMock()
        first.status_code = 429
        first.raise_for_status.return_value = None
        second = _mock_response(repeaters)
        second.status_code = 200

        client.session.get = MagicMock(side_effect=[first, second])

        with patch("plugsmith.builder.api.time.sleep"):
            result = client.fetch_state("MO")
        assert result == repeaters

    def test_handles_429_all_retries_exhausted_returns_empty(self, tmp_path):
        client = _make_client(tmp_path)

        always_429 = MagicMock()
        always_429.status_code = 429
        always_429.raise_for_status.return_value = None

        # 1 initial + 3 retries = 4 calls, all 429
        client.session.get = MagicMock(return_value=always_429)

        with patch("plugsmith.builder.api.time.sleep"):
            result = client.fetch_state("MO")

        assert result == []
        assert client.session.get.call_count == 4  # 1 initial + 3 retries

    def test_request_exception_returns_empty_no_cache(self, tmp_path):
        client = _make_client(tmp_path)
        client.session.get = MagicMock(side_effect=requests.RequestException("timeout"))
        result = client.fetch_state("MO")
        assert result == []

    def test_request_exception_returns_stale_cache(self, tmp_path):
        client = _make_client(tmp_path)
        stale = [{"Callsign": "W0STALE"}]
        cache_file = Path(client.cache_dir) / "state_29.json"
        cache_file.write_text(json.dumps(stale))
        # Make cache appear stale by setting mtime far in the past
        old_time = time.time() - (800 * 3600)
        import os
        os.utime(cache_file, (old_time, old_time))

        client.session.get = MagicMock(side_effect=requests.RequestException("error"))
        result = client.fetch_state("MO")
        assert result == stale


# ---------------------------------------------------------------------------
# fetch_states
# ---------------------------------------------------------------------------


class TestFetchStates:
    def test_aggregates_multiple_states(self, tmp_path):
        client = _make_client(tmp_path)
        mo_data = [{"Callsign": "W0MO"}]
        ks_data = [{"Callsign": "W0KS"}]

        # Pre-populate caches
        (Path(client.cache_dir) / "state_29.json").write_text(json.dumps(mo_data))
        (Path(client.cache_dir) / "state_20.json").write_text(json.dumps(ks_data))

        result = client.fetch_states(["MO", "KS"])
        assert len(result) == 2
        callsigns = {r["Callsign"] for r in result}
        assert callsigns == {"W0MO", "W0KS"}


# ---------------------------------------------------------------------------
# clear_cache
# ---------------------------------------------------------------------------


class TestClearCache:
    def test_clear_single_state(self, tmp_path):
        client = _make_client(tmp_path)
        cache_file = Path(client.cache_dir) / "state_29.json"
        cache_file.write_text("[]")
        deleted = client.clear_cache("MO")
        assert deleted == 1
        assert not cache_file.exists()

    def test_clear_single_state_missing_file(self, tmp_path):
        client = _make_client(tmp_path)
        deleted = client.clear_cache("MO")
        assert deleted == 0

    def test_clear_unknown_state_returns_zero(self, tmp_path):
        client = _make_client(tmp_path)
        assert client.clear_cache("ZZ") == 0

    def test_clear_all_states(self, tmp_path):
        client = _make_client(tmp_path)
        for state_id in ["01", "02", "04"]:
            (Path(client.cache_dir) / f"state_{state_id}.json").write_text("[]")
        deleted = client.clear_cache()
        assert deleted == 3
        assert list((Path(client.cache_dir)).glob("state_*.json")) == []


# ---------------------------------------------------------------------------
# US_STATES dict
# ---------------------------------------------------------------------------


class TestUSStates:
    def test_has_fifty_states_and_dc(self):
        assert len(US_STATES) == 51  # 50 states + DC

    def test_all_values_are_id_name_tuples(self):
        for abbr, (state_id, name) in US_STATES.items():
            assert len(abbr) == 2
            assert abbr.isupper()
            assert state_id.isdigit()
            assert name

    def test_missouri_present(self):
        assert "MO" in US_STATES
        assert US_STATES["MO"][1] == "Missouri"
