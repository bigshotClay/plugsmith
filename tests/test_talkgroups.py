"""Tests for the talkgroups module: TalkgroupClient, RadioIDClient, TalkgroupRegistry."""

import base64
import json
import os
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import requests

import pytest

from plugsmith.builder.talkgroups import (
    CORE_TG_IDS,
    PRIVATE_CALL_TGS,
    RadioIDClient,
    RepeaterTGData,
    TalkgroupClient,
    TalkgroupInfo,
    TalkgroupRegistry,
)


# ---------------------------------------------------------------------------
# TalkgroupRegistry
# ---------------------------------------------------------------------------


class TestTalkgroupRegistry:
    def _registry(self, tgs: dict[int, TalkgroupInfo]) -> TalkgroupRegistry:
        return TalkgroupRegistry(tgs)

    def test_name_returns_registry_name(self):
        reg = self._registry({9: TalkgroupInfo(tg_id=9, name="Local")})
        assert reg.name(9) == "Local"

    def test_name_fallback_for_unknown_tg(self):
        reg = self._registry({})
        # Unknown TG ID → falls back to legacy tg_name() which returns "TG {num}"
        assert reg.name(99999) == "TG 99999"

    def test_name_fallback_uses_tg_names_dict(self):
        reg = self._registry({})
        # Well-known TGs handled by legacy tg_name()
        assert reg.name(3100) == "US National"
        assert reg.name(9) == "Local"

    def test_call_type_from_registry(self):
        reg = self._registry({9: TalkgroupInfo(tg_id=9, name="Local", call_type="GroupCall")})
        assert reg.call_type(9) == "GroupCall"

    def test_call_type_private_call_for_known_private_ids(self):
        reg = self._registry({})
        assert reg.call_type(9998) == "PrivateCall"
        assert reg.call_type(4000) == "PrivateCall"

    def test_call_type_default_group_call(self):
        reg = self._registry({})
        assert reg.call_type(3100) == "GroupCall"

    def test_all_tgs_returns_all_entries(self):
        tgs = {
            9: TalkgroupInfo(9, "Local"),
            3100: TalkgroupInfo(3100, "US National"),
        }
        reg = self._registry(tgs)
        assert len(reg.all_tgs()) == 2

    def test_len(self):
        reg = self._registry({9: TalkgroupInfo(9, "Local")})
        assert len(reg) == 1

    def test_contains(self):
        reg = self._registry({9: TalkgroupInfo(9, "Local")})
        assert 9 in reg
        assert 3100 not in reg


# ---------------------------------------------------------------------------
# TalkgroupClient — BrandMeister fetch and cache
# ---------------------------------------------------------------------------


class TestTalkgroupClientBrandMeister:
    def _bm_response(self) -> list[dict]:
        return [
            {"id": 9, "name": "Local"},
            {"id": 3100, "name": "US National"},
            {"id": 93, "name": "North America"},
        ]

    def test_brandmeister_fetch_populates_registry(self, tmp_path):
        with patch("plugsmith.builder.talkgroups.requests.Session") as MockSession:
            mock_resp = MagicMock()
            mock_resp.json.return_value = self._bm_response()
            mock_resp.raise_for_status = MagicMock()
            MockSession.return_value.get.return_value = mock_resp
            MockSession.return_value.headers = {}

            client = TalkgroupClient(cache_dir=str(tmp_path), rate_limit=0)
            reg = client.fetch_registry(networks=["brandmeister"])

        assert 9 in reg
        assert reg.name(9) == "Local"
        assert reg.name(3100) == "US National"

    def test_brandmeister_cache_written(self, tmp_path):
        with patch("plugsmith.builder.talkgroups.requests.Session") as MockSession:
            mock_resp = MagicMock()
            mock_resp.json.return_value = self._bm_response()
            mock_resp.raise_for_status = MagicMock()
            MockSession.return_value.get.return_value = mock_resp
            MockSession.return_value.headers = {}

            client = TalkgroupClient(cache_dir=str(tmp_path), rate_limit=0)
            client.fetch_registry(networks=["brandmeister"])

        assert (tmp_path / "tg_brandmeister.json").exists()

    def test_brandmeister_cache_hit_skips_network(self, tmp_path):
        cache_file = tmp_path / "tg_brandmeister.json"
        cache_file.write_text(json.dumps(self._bm_response()))

        with patch("plugsmith.builder.talkgroups.requests.Session") as MockSession:
            MockSession.return_value.headers = {}
            client = TalkgroupClient(cache_dir=str(tmp_path), rate_limit=0)
            reg = client.fetch_registry(networks=["brandmeister"])
            MockSession.return_value.get.assert_not_called()

        assert 9 in reg

    def test_brandmeister_filters_invalid_ids(self, tmp_path):
        raw = [{"id": 0, "name": "Bad"}, {"id": -1, "name": "Neg"}, {"id": 9, "name": "Local"}]
        with patch("plugsmith.builder.talkgroups.requests.Session") as MockSession:
            mock_resp = MagicMock()
            mock_resp.json.return_value = raw
            mock_resp.raise_for_status = MagicMock()
            MockSession.return_value.get.return_value = mock_resp
            MockSession.return_value.headers = {}

            client = TalkgroupClient(cache_dir=str(tmp_path), rate_limit=0)
            reg = client.fetch_registry(networks=["brandmeister"])

        assert len(reg) == 1
        assert 9 in reg

    def test_brandmeister_error_body_as_200_handled_gracefully(self, tmp_path):
        """BrandMeister sometimes returns an error dict with 200 OK (e.g. rate limit).
        list(raw.values()) yields strings which raise AttributeError on .get() — must not crash."""
        raw = {"error": "Too many requests", "status": "429"}
        with patch("plugsmith.builder.talkgroups.requests.Session") as MockSession:
            mock_resp = MagicMock()
            mock_resp.json.return_value = raw
            mock_resp.raise_for_status = MagicMock()
            MockSession.return_value.get.return_value = mock_resp
            MockSession.return_value.headers = {}

            client = TalkgroupClient(cache_dir=str(tmp_path), rate_limit=0)
            reg = client.fetch_registry(networks=["brandmeister"])

        assert len(reg) == 0  # no valid TGs parsed, but no crash

    def test_brandmeister_dict_response_handled(self, tmp_path):
        """BrandMeister may return a dict keyed by TG ID instead of a list."""
        raw = {"9": {"id": 9, "name": "Local"}, "93": {"id": 93, "name": "NAm"}}
        with patch("plugsmith.builder.talkgroups.requests.Session") as MockSession:
            mock_resp = MagicMock()
            mock_resp.json.return_value = raw
            mock_resp.raise_for_status = MagicMock()
            MockSession.return_value.get.return_value = mock_resp
            MockSession.return_value.headers = {}

            client = TalkgroupClient(cache_dir=str(tmp_path), rate_limit=0)
            reg = client.fetch_registry(networks=["brandmeister"])

        assert 9 in reg
        assert 93 in reg


# ---------------------------------------------------------------------------
# TalkgroupClient — TGIF fetch and base64 decoding
# ---------------------------------------------------------------------------


class TestTalkgroupClientTGIF:
    def _tgif_response(self) -> list[dict]:
        desc = base64.b64encode(b"World-wide calling").decode()
        return [
            {"id": "1", "name": "Worldwide", "description": desc, "website": ""},
            {"id": "91", "name": "WW 1", "description": "", "website": ""},
        ]

    def test_tgif_fetch_populates_registry(self, tmp_path):
        with patch("plugsmith.builder.talkgroups.requests.Session") as MockSession:
            mock_resp = MagicMock()
            mock_resp.json.return_value = self._tgif_response()
            mock_resp.raise_for_status = MagicMock()
            MockSession.return_value.get.return_value = mock_resp
            MockSession.return_value.headers = {}

            client = TalkgroupClient(cache_dir=str(tmp_path), rate_limit=0)
            reg = client.fetch_registry(networks=["tgif"])

        assert 1 in reg
        assert reg.name(1) == "Worldwide"

    def test_tgif_base64_description_decoded(self, tmp_path):
        with patch("plugsmith.builder.talkgroups.requests.Session") as MockSession:
            mock_resp = MagicMock()
            mock_resp.json.return_value = self._tgif_response()
            mock_resp.raise_for_status = MagicMock()
            MockSession.return_value.get.return_value = mock_resp
            MockSession.return_value.headers = {}

            client = TalkgroupClient(cache_dir=str(tmp_path), rate_limit=0)
            reg = client.fetch_registry(networks=["tgif"])

        entry = next(t for t in reg.all_tgs() if t.tg_id == 1)
        assert "World-wide calling" in entry.description

    def test_tgif_cache_written(self, tmp_path):
        with patch("plugsmith.builder.talkgroups.requests.Session") as MockSession:
            mock_resp = MagicMock()
            mock_resp.json.return_value = self._tgif_response()
            mock_resp.raise_for_status = MagicMock()
            MockSession.return_value.get.return_value = mock_resp
            MockSession.return_value.headers = {}

            client = TalkgroupClient(cache_dir=str(tmp_path), rate_limit=0)
            client.fetch_registry(networks=["tgif"])

        assert (tmp_path / "tg_tgif.json").exists()

    def test_tgif_cache_hit_skips_network(self, tmp_path):
        cache_file = tmp_path / "tg_tgif.json"
        cache_file.write_text(json.dumps(self._tgif_response()))

        with patch("plugsmith.builder.talkgroups.requests.Session") as MockSession:
            MockSession.return_value.headers = {}
            client = TalkgroupClient(cache_dir=str(tmp_path), rate_limit=0)
            reg = client.fetch_registry(networks=["tgif"])
            MockSession.return_value.get.assert_not_called()

        assert 1 in reg


# ---------------------------------------------------------------------------
# TalkgroupClient — registry merge priority
# ---------------------------------------------------------------------------


class TestTalkgroupClientMergePriority:
    def test_brandmeister_wins_on_conflict(self, tmp_path):
        tgif_raw = [{"id": "9", "name": "TGIF Local", "description": ""}]
        bm_raw = [{"id": 9, "name": "BM Local"}]

        # Write both caches so no network call is needed
        (tmp_path / "tg_tgif.json").write_text(json.dumps(tgif_raw))
        (tmp_path / "tg_brandmeister.json").write_text(json.dumps(bm_raw))

        with patch("plugsmith.builder.talkgroups.requests.Session") as MockSession:
            MockSession.return_value.headers = {}
            client = TalkgroupClient(cache_dir=str(tmp_path), rate_limit=0)
            reg = client.fetch_registry(networks=["brandmeister", "tgif"])

        assert reg.name(9) == "BM Local"

    def test_private_call_type_enforced(self, tmp_path):
        bm_raw = [{"id": 9998, "name": "Parrot"}, {"id": 4000, "name": "Disconnect"}]
        (tmp_path / "tg_brandmeister.json").write_text(json.dumps(bm_raw))

        with patch("plugsmith.builder.talkgroups.requests.Session") as MockSession:
            MockSession.return_value.headers = {}
            client = TalkgroupClient(cache_dir=str(tmp_path), rate_limit=0)
            reg = client.fetch_registry(networks=["brandmeister"])

        assert reg.call_type(9998) == "PrivateCall"
        assert reg.call_type(4000) == "PrivateCall"


# ---------------------------------------------------------------------------
# TalkgroupClient — clear_cache
# ---------------------------------------------------------------------------


class TestTalkgroupClientClearCache:
    def test_clear_cache_removes_files(self, tmp_path):
        (tmp_path / "tg_brandmeister.json").write_text("[]")
        (tmp_path / "tg_tgif.json").write_text("[]")

        with patch("plugsmith.builder.talkgroups.requests.Session") as MockSession:
            MockSession.return_value.headers = {}
            client = TalkgroupClient(cache_dir=str(tmp_path))
            count = client.clear_cache()

        assert count == 2
        assert not (tmp_path / "tg_brandmeister.json").exists()
        assert not (tmp_path / "tg_tgif.json").exists()

    def test_clear_cache_returns_zero_when_no_files(self, tmp_path):
        with patch("plugsmith.builder.talkgroups.requests.Session") as MockSession:
            MockSession.return_value.headers = {}
            client = TalkgroupClient(cache_dir=str(tmp_path))
            assert client.clear_cache() == 0


# ---------------------------------------------------------------------------
# RadioIDClient — fetch and cache
# ---------------------------------------------------------------------------


def _radioid_response(callsigns: list[str]) -> dict:
    return {
        "count": len(callsigns),
        "results": [
            {
                "callsign": cs,
                "ts1_static_talkgroups": [9, 3129],
                "ts2_static_talkgroups": [3100, 93],
            }
            for cs in callsigns
        ],
    }


class TestRadioIDClient:
    def test_fetch_returns_callsign_map(self, tmp_path):
        raw = _radioid_response(["W0ABC", "W0XYZ"])
        with patch("plugsmith.builder.talkgroups.requests.Session") as MockSession:
            mock_resp = MagicMock()
            mock_resp.json.return_value = raw
            mock_resp.raise_for_status = MagicMock()
            MockSession.return_value.get.return_value = mock_resp
            MockSession.return_value.headers = {}

            client = RadioIDClient(cache_dir=str(tmp_path), rate_limit=0)
            result = client.fetch_repeater_tgs("MO")

        assert "W0ABC" in result
        assert result["W0ABC"].ts1_static == [9, 3129]
        assert result["W0ABC"].ts2_static == [3100, 93]

    def test_fetch_normalizes_callsign_to_uppercase(self, tmp_path):
        raw = {"count": 1, "results": [{"callsign": "w0abc", "ts1_static_talkgroups": [9], "ts2_static_talkgroups": []}]}
        with patch("plugsmith.builder.talkgroups.requests.Session") as MockSession:
            mock_resp = MagicMock()
            mock_resp.json.return_value = raw
            mock_resp.raise_for_status = MagicMock()
            MockSession.return_value.get.return_value = mock_resp
            MockSession.return_value.headers = {}

            client = RadioIDClient(cache_dir=str(tmp_path), rate_limit=0)
            result = client.fetch_repeater_tgs("MO")

        assert "W0ABC" in result

    def test_fetch_cache_written(self, tmp_path):
        with patch("plugsmith.builder.talkgroups.requests.Session") as MockSession:
            mock_resp = MagicMock()
            mock_resp.json.return_value = _radioid_response(["W0ABC"])
            mock_resp.raise_for_status = MagicMock()
            MockSession.return_value.get.return_value = mock_resp
            MockSession.return_value.headers = {}

            client = RadioIDClient(cache_dir=str(tmp_path), rate_limit=0)
            client.fetch_repeater_tgs("MO")

        assert (tmp_path / "radioid_MO.json").exists()

    def test_fetch_cache_hit_skips_network(self, tmp_path):
        cache_file = tmp_path / "radioid_MO.json"
        cache_file.write_text(json.dumps(_radioid_response(["W0ABC"])))

        with patch("plugsmith.builder.talkgroups.requests.Session") as MockSession:
            MockSession.return_value.headers = {}
            client = RadioIDClient(cache_dir=str(tmp_path), rate_limit=0)
            result = client.fetch_repeater_tgs("MO")
            MockSession.return_value.get.assert_not_called()

        assert "W0ABC" in result

    def test_fetch_unknown_state_returns_empty(self, tmp_path):
        with patch("plugsmith.builder.talkgroups.requests.Session") as MockSession:
            MockSession.return_value.headers = {}
            client = RadioIDClient(cache_dir=str(tmp_path), rate_limit=0)
            result = client.fetch_repeater_tgs("XX")

        assert result == {}

    def test_fetch_states_merges_multiple(self, tmp_path):
        mo_raw = _radioid_response(["W0MO"])
        il_raw = _radioid_response(["W0IL"])

        def _get(url, params=None, timeout=None):
            state = (params or {}).get("state", "")
            resp = MagicMock()
            resp.raise_for_status = MagicMock()
            if "Missouri" in state:
                resp.json.return_value = mo_raw
            else:
                resp.json.return_value = il_raw
            return resp

        with patch("plugsmith.builder.talkgroups.requests.Session") as MockSession:
            MockSession.return_value.get.side_effect = _get
            MockSession.return_value.headers = {}
            client = RadioIDClient(cache_dir=str(tmp_path), rate_limit=0)
            result = client.fetch_states(["MO", "IL"])

        assert "W0MO" in result
        assert "W0IL" in result

    def test_clear_cache_single_state(self, tmp_path):
        (tmp_path / "radioid_MO.json").write_text("{}")
        (tmp_path / "radioid_IL.json").write_text("{}")

        with patch("plugsmith.builder.talkgroups.requests.Session") as MockSession:
            MockSession.return_value.headers = {}
            client = RadioIDClient(cache_dir=str(tmp_path))
            count = client.clear_cache("MO")

        assert count == 1
        assert not (tmp_path / "radioid_MO.json").exists()
        assert (tmp_path / "radioid_IL.json").exists()

    def test_clear_cache_all(self, tmp_path):
        (tmp_path / "radioid_MO.json").write_text("{}")
        (tmp_path / "radioid_IL.json").write_text("{}")

        with patch("plugsmith.builder.talkgroups.requests.Session") as MockSession:
            MockSession.return_value.headers = {}
            client = RadioIDClient(cache_dir=str(tmp_path))
            count = client.clear_cache()

        assert count == 2


# ---------------------------------------------------------------------------
# Integration with codeplug.py — contact fill ordering and cap
# ---------------------------------------------------------------------------


class TestContactFill:
    def _make_zone_with_tg(self, tg_num: int) -> dict:
        return {
            "name": f"Zone {tg_num}",
            "tier": "home",
            "state": "MO",
            "channels": [{
                "ch_type": "digital",
                "name": f"Test {tg_num}",
                "rx_freq": 444.100,
                "tx_freq": 449.100,
                "color_code": 1,
                "time_slot": 1,
                "tg_num": tg_num,
                "tg_name": "Local",
            }],
        }

    def test_in_use_tgs_always_present(self, tmp_path):
        from plugsmith.builder.codeplug import generate_codeplug_yaml
        zones = [self._make_zone_with_tg(31337)]
        codeplug = generate_codeplug_yaml(zones, dmr_id=1234567, callsign="W0TEST")
        contact_nums = {c["dmr"]["number"] for c in codeplug["contacts"]}
        assert 31337 in contact_nums

    def test_fill_contacts_adds_registry_tgs(self, tmp_path):
        from plugsmith.builder.codeplug import generate_codeplug_yaml
        # Build a small registry with TG 12345 not used by any channel
        registry_tgs = {12345: TalkgroupInfo(12345, "Test TG")}
        reg = TalkgroupRegistry(registry_tgs)
        zones = [self._make_zone_with_tg(9)]
        codeplug = generate_codeplug_yaml(
            zones, dmr_id=1234567, callsign="W0TEST",
            tg_registry=reg, radio_max_tgs=500
        )
        contact_nums = {c["dmr"]["number"] for c in codeplug["contacts"]}
        assert 12345 in contact_nums

    def test_fill_contacts_respects_cap(self):
        from plugsmith.builder.codeplug import generate_codeplug_yaml
        # Build a large registry
        tgs = {i: TalkgroupInfo(i, f"TG {i}") for i in range(1, 10000)}
        reg = TalkgroupRegistry(tgs)
        zones = [self._make_zone_with_tg(9)]
        cap = 50
        codeplug = generate_codeplug_yaml(
            zones, dmr_id=1234567, callsign="W0TEST",
            tg_registry=reg, radio_max_tgs=cap
        )
        assert len(codeplug["contacts"]) <= cap

    def test_fill_contacts_in_use_first(self):
        from plugsmith.builder.codeplug import generate_codeplug_yaml
        # Use an unusual TG (99999) and fill with a small cap
        tgs = {i: TalkgroupInfo(i, f"TG {i}") for i in range(1, 100)}
        reg = TalkgroupRegistry(tgs)
        zones = [self._make_zone_with_tg(99999)]  # not in registry
        codeplug = generate_codeplug_yaml(
            zones, dmr_id=1234567, callsign="W0TEST",
            tg_registry=reg, radio_max_tgs=10
        )
        contact_nums = {c["dmr"]["number"] for c in codeplug["contacts"]}
        # In-use TG must survive even though it's not in the registry
        assert 99999 in contact_nums

    def test_gl_all_contains_only_in_use_tgs(self):
        from plugsmith.builder.codeplug import generate_codeplug_yaml
        tgs = {i: TalkgroupInfo(i, f"TG {i}") for i in range(1, 200)}
        reg = TalkgroupRegistry(tgs)
        zones = [self._make_zone_with_tg(9)]
        codeplug = generate_codeplug_yaml(
            zones, dmr_id=1234567, callsign="W0TEST",
            tg_registry=reg, radio_max_tgs=500
        )
        # gl_all should have in-use TGs only (9 and always-present 9998, 4000 minus private)
        gl_all = next(g for g in codeplug["groupLists"] if g["id"] == "gl_all")
        # Should not contain every registry TG
        assert len(gl_all["contacts"]) < 500

    def test_registry_names_used_in_contacts(self):
        from plugsmith.builder.codeplug import generate_codeplug_yaml
        tgs = {9: TalkgroupInfo(9, "MyLocalName")}
        reg = TalkgroupRegistry(tgs)
        zones = [self._make_zone_with_tg(9)]
        codeplug = generate_codeplug_yaml(
            zones, dmr_id=1234567, callsign="W0TEST",
            tg_registry=reg
        )
        tg9_contact = next(c["dmr"] for c in codeplug["contacts"] if c["dmr"]["number"] == 9)
        assert tg9_contact["name"] == "MyLocalName"


# ---------------------------------------------------------------------------
# Integration with zones.py — RadioID TG data in home_state_channels
# ---------------------------------------------------------------------------


class TestHomeChannelsWithRadioID:
    def _dmr_repeater(self, callsign="W0TEST"):
        from tests.conftest import make_repeater
        return make_repeater(
            callsign=callsign,
            frequency=444.100,
            input_freq=449.100,
            is_fm=False,
            is_dmr=True,
            dmr_color_code=1,
            pl_tone=None,
        )

    def test_uses_radioid_ts1_when_present(self):
        from plugsmith.builder.zones import home_state_channels
        r = self._dmr_repeater("W0TEST")
        radioid_map = {
            "W0TEST": RepeaterTGData(callsign="W0TEST", ts1_static=[50001, 50002], ts2_static=[3100]),
        }
        channels = home_state_channels("MO", [r], {}, {}, repeater_tg_map=radioid_map)
        digital = [ch for ch in channels if ch["ch_type"] == "digital"]
        tg_nums = [ch["tg_num"] for ch in digital]
        assert 50001 in tg_nums
        assert 50002 in tg_nums

    def test_uses_radioid_ts2_when_present(self):
        from plugsmith.builder.zones import home_state_channels
        r = self._dmr_repeater("W0TEST")
        radioid_map = {
            "W0TEST": RepeaterTGData(callsign="W0TEST", ts1_static=[9], ts2_static=[99901, 99902]),
        }
        channels = home_state_channels("MO", [r], {}, {}, repeater_tg_map=radioid_map)
        digital = [ch for ch in channels if ch["ch_type"] == "digital"]
        tg_nums = [ch["tg_num"] for ch in digital]
        assert 99901 in tg_nums

    def test_falls_back_to_defaults_when_no_radioid_data(self):
        from plugsmith.builder.zones import home_state_channels
        r = self._dmr_repeater("W0NOREC")
        radioid_map = {}  # no data for this repeater
        channels = home_state_channels("MO", [r], {}, {"MO": 3129}, repeater_tg_map=radioid_map)
        digital = [ch for ch in channels if ch["ch_type"] == "digital"]
        tg_nums = [ch["tg_num"] for ch in digital]
        # Default slots: Local (9), Regional (8), State (3129), US Natl (3100), ...
        assert 9 in tg_nums
        assert 8 in tg_nums
        assert 3129 in tg_nums

    def test_falls_back_when_radioid_map_is_none(self):
        from plugsmith.builder.zones import home_state_channels
        r = self._dmr_repeater("W0TEST")
        channels = home_state_channels("MO", [r], {}, {"MO": 3129}, repeater_tg_map=None)
        digital = [ch for ch in channels if ch["ch_type"] == "digital"]
        tg_nums = [ch["tg_num"] for ch in digital]
        assert 9 in tg_nums

    def test_respects_max_tgs_per_repeater_cap(self):
        from plugsmith.builder.zones import home_state_channels
        r = self._dmr_repeater("W0TEST")
        # RadioID has 10 TS1 TGs
        radioid_map = {
            "W0TEST": RepeaterTGData(
                callsign="W0TEST",
                ts1_static=list(range(50001, 50011)),
                ts2_static=list(range(60001, 60011)),
            ),
        }
        config = {"home_region": {"dmr_talkgroups_per_repeater": 4}}
        channels = home_state_channels("MO", [r], config, {}, repeater_tg_map=radioid_map)
        digital = [ch for ch in channels if ch["ch_type"] == "digital"]
        assert len(digital) == 4

    def test_callsign_lookup_case_insensitive(self):
        from plugsmith.builder.zones import home_state_channels
        r = self._dmr_repeater("w0test")  # lowercase callsign
        radioid_map = {
            "W0TEST": RepeaterTGData(callsign="W0TEST", ts1_static=[55555], ts2_static=[]),
        }
        channels = home_state_channels("MO", [r], {}, {}, repeater_tg_map=radioid_map)
        digital = [ch for ch in channels if ch["ch_type"] == "digital"]
        tg_nums = [ch["tg_num"] for ch in digital]
        assert 55555 in tg_nums


# ---------------------------------------------------------------------------
# build_config.py — talkgroups section in DEFAULT_CONFIG
# ---------------------------------------------------------------------------


class TestBuildConfigDefaults:
    def test_talkgroups_section_exists(self):
        from plugsmith.builder.build_config import DEFAULT_CONFIG
        assert "talkgroups" in DEFAULT_CONFIG

    def test_default_networks(self):
        from plugsmith.builder.build_config import DEFAULT_CONFIG
        networks = DEFAULT_CONFIG["talkgroups"]["networks"]
        assert "brandmeister" in networks
        assert "tgif" in networks

    def test_fill_contacts_enabled_by_default(self):
        from plugsmith.builder.build_config import DEFAULT_CONFIG
        assert DEFAULT_CONFIG["talkgroups"]["fill_contacts"] is True

    def test_per_repeater_lookup_enabled_by_default(self):
        from plugsmith.builder.build_config import DEFAULT_CONFIG
        assert DEFAULT_CONFIG["talkgroups"]["per_repeater_lookup"] is True

    def test_load_config_preserves_talkgroups_section(self, tmp_path):
        from plugsmith.builder.build_config import load_config
        # Empty config file — defaults should be used
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text("dmr_id: 1234567\ncallsign: W0TEST\napi_email: test@example.com\n")
        config = load_config(str(cfg_file))
        assert "talkgroups" in config
        assert config["talkgroups"]["fill_contacts"] is True


# ---------------------------------------------------------------------------
# TalkgroupClient — _notify with progress_callback (line 133)
# ---------------------------------------------------------------------------


class TestTalkgroupClientNotify:
    def test_notify_called_with_progress_callback(self, tmp_path):
        """Line 133: _notify calls progress_callback when set."""
        calls = []
        cache_file = tmp_path / "tg_brandmeister.json"
        cache_file.write_text(json.dumps([{"id": 9, "name": "Local"}]))

        with patch("plugsmith.builder.talkgroups.requests.Session") as MockSession:
            MockSession.return_value.headers = {}
            client = TalkgroupClient(
                cache_dir=str(tmp_path),
                rate_limit=0,
                progress_callback=lambda msg, cached: calls.append((msg, cached)),
            )
            client.fetch_registry(networks=["brandmeister"])

        assert any("BrandMeister" in msg for msg, _ in calls)


# ---------------------------------------------------------------------------
# TalkgroupClient — BrandMeister error handling (lines 153-160, 173-174)
# ---------------------------------------------------------------------------


class TestTalkgroupClientBrandMeisterErrors:
    def test_request_exception_no_cache_returns_empty(self, tmp_path):
        """Lines 153-160: BrandMeister fetch exception with no cache returns empty registry."""
        with patch("plugsmith.builder.talkgroups.requests.Session") as MockSession:
            MockSession.return_value.get.side_effect = requests.RequestException("timeout")
            MockSession.return_value.headers = {}
            client = TalkgroupClient(cache_dir=str(tmp_path), rate_limit=0)
            reg = client.fetch_registry(networks=["brandmeister"])

        assert len(reg) == 0

    def test_request_exception_stale_cache_returns_data(self, tmp_path):
        """Lines 153-160: BrandMeister fetch exception with stale cache returns stale data."""
        stale_data = [{"id": 9, "name": "Local"}]
        cache_file = tmp_path / "tg_brandmeister.json"
        cache_file.write_text(json.dumps(stale_data))
        old_time = time.time() - (800 * 3600)  # 800 hours > 168h cache max age
        os.utime(cache_file, (old_time, old_time))

        with patch("plugsmith.builder.talkgroups.requests.Session") as MockSession:
            MockSession.return_value.get.side_effect = requests.RequestException("timeout")
            MockSession.return_value.headers = {}
            client = TalkgroupClient(cache_dir=str(tmp_path), rate_limit=0)
            reg = client.fetch_registry(networks=["brandmeister"])

        assert 9 in reg

    def test_malformed_item_skipped(self, tmp_path):
        """Lines 173-174: BrandMeister malformed item (bad id) causes ValueError → skipped."""
        raw = [{"id": "NOT-AN-INT"}, {"id": 9, "name": "Local"}]
        with patch("plugsmith.builder.talkgroups.requests.Session") as MockSession:
            mock_resp = MagicMock()
            mock_resp.json.return_value = raw
            mock_resp.raise_for_status = MagicMock()
            MockSession.return_value.get.return_value = mock_resp
            MockSession.return_value.headers = {}
            client = TalkgroupClient(cache_dir=str(tmp_path), rate_limit=0)
            reg = client.fetch_registry(networks=["brandmeister"])

        assert 9 in reg


# ---------------------------------------------------------------------------
# TalkgroupClient — TGIF error handling (lines 194-201, 209, 214-215, 220-221)
# ---------------------------------------------------------------------------


class TestTalkgroupClientTGIFErrors:
    def test_request_exception_no_cache_returns_empty(self, tmp_path):
        """Lines 194-201: TGIF fetch exception with no cache returns empty registry."""
        with patch("plugsmith.builder.talkgroups.requests.Session") as MockSession:
            MockSession.return_value.get.side_effect = requests.RequestException("timeout")
            MockSession.return_value.headers = {}
            client = TalkgroupClient(cache_dir=str(tmp_path), rate_limit=0)
            reg = client.fetch_registry(networks=["tgif"])

        assert len(reg) == 0

    def test_request_exception_stale_cache_returns_data(self, tmp_path):
        """Lines 194-201: TGIF fetch exception with stale cache returns stale data."""
        stale_data = [{"id": "91", "name": "WW", "description": ""}]
        cache_file = tmp_path / "tg_tgif.json"
        cache_file.write_text(json.dumps(stale_data))
        old_time = time.time() - (800 * 3600)  # 800 hours > 168h cache max age
        os.utime(cache_file, (old_time, old_time))

        with patch("plugsmith.builder.talkgroups.requests.Session") as MockSession:
            MockSession.return_value.get.side_effect = requests.RequestException("timeout")
            MockSession.return_value.headers = {}
            client = TalkgroupClient(cache_dir=str(tmp_path), rate_limit=0)
            reg = client.fetch_registry(networks=["tgif"])

        assert 91 in reg

    def test_zero_tg_id_skipped(self, tmp_path):
        """Line 209: TGIF item with tg_id <= 0 is skipped."""
        raw = [{"id": "0", "name": "Bad"}, {"id": "91", "name": "WW", "description": ""}]
        with patch("plugsmith.builder.talkgroups.requests.Session") as MockSession:
            mock_resp = MagicMock()
            mock_resp.json.return_value = raw
            mock_resp.raise_for_status = MagicMock()
            MockSession.return_value.get.return_value = mock_resp
            MockSession.return_value.headers = {}
            client = TalkgroupClient(cache_dir=str(tmp_path), rate_limit=0)
            reg = client.fetch_registry(networks=["tgif"])

        assert 0 not in reg
        assert 91 in reg

    def test_bad_base64_handled_gracefully(self, tmp_path):
        """Lines 214-215: TGIF None description causes TypeError → desc='', item still added."""
        raw = [{"id": "91", "name": "WW", "description": None}]
        with patch("plugsmith.builder.talkgroups.requests.Session") as MockSession:
            mock_resp = MagicMock()
            mock_resp.json.return_value = raw
            mock_resp.raise_for_status = MagicMock()
            MockSession.return_value.get.return_value = mock_resp
            MockSession.return_value.headers = {}
            client = TalkgroupClient(cache_dir=str(tmp_path), rate_limit=0)
            reg = client.fetch_registry(networks=["tgif"])

        assert 91 in reg

    def test_malformed_item_skipped(self, tmp_path):
        """Lines 220-221: TGIF malformed item (bad id) causes ValueError → skipped."""
        raw = [{"id": "NOT-AN-INT"}, {"id": "91", "name": "WW", "description": ""}]
        with patch("plugsmith.builder.talkgroups.requests.Session") as MockSession:
            mock_resp = MagicMock()
            mock_resp.json.return_value = raw
            mock_resp.raise_for_status = MagicMock()
            MockSession.return_value.get.return_value = mock_resp
            MockSession.return_value.headers = {}
            client = TalkgroupClient(cache_dir=str(tmp_path), rate_limit=0)
            reg = client.fetch_registry(networks=["tgif"])

        assert 91 in reg


# ---------------------------------------------------------------------------
# TalkgroupClient — fetch_registry default networks (line 234)
# ---------------------------------------------------------------------------


class TestFetchRegistryDefaultNetworks:
    def test_default_networks_fetches_both(self, tmp_path):
        """Line 234: fetch_registry(networks=None) defaults to ['brandmeister', 'tgif']."""
        bm_data = [{"id": 9, "name": "Local"}]
        tgif_data = [{"id": "91", "name": "WW", "description": ""}]
        (tmp_path / "tg_brandmeister.json").write_text(json.dumps(bm_data))
        (tmp_path / "tg_tgif.json").write_text(json.dumps(tgif_data))

        with patch("plugsmith.builder.talkgroups.requests.Session") as MockSession:
            MockSession.return_value.headers = {}
            client = TalkgroupClient(cache_dir=str(tmp_path), rate_limit=0)
            reg = client.fetch_registry()  # networks=None → default

        assert 9 in reg
        assert 91 in reg


# ---------------------------------------------------------------------------
# RadioIDClient — error handling (lines 301, 338-345, 351, 373)
# ---------------------------------------------------------------------------


class TestRadioIDClientErrors:
    def test_notify_with_progress_callback(self, tmp_path):
        """Line 301: RadioIDClient._notify calls progress_callback when set."""
        calls = []
        cache_file = tmp_path / "radioid_MO.json"
        cache_file.write_text(json.dumps({"count": 0, "results": []}))

        with patch("plugsmith.builder.talkgroups.requests.Session") as MockSession:
            MockSession.return_value.headers = {}
            client = RadioIDClient(
                cache_dir=str(tmp_path),
                rate_limit=0,
                progress_callback=lambda msg, cached: calls.append((msg, cached)),
            )
            client.fetch_repeater_tgs("MO")

        assert any("MO" in msg for msg, _ in calls)

    def test_request_exception_no_cache_returns_empty(self, tmp_path):
        """Lines 338-345: RadioID fetch exception with no cache returns {}."""
        with patch("plugsmith.builder.talkgroups.requests.Session") as MockSession:
            MockSession.return_value.get.side_effect = requests.RequestException("timeout")
            MockSession.return_value.headers = {}
            client = RadioIDClient(cache_dir=str(tmp_path), rate_limit=0)
            result = client.fetch_repeater_tgs("MO")

        assert result == {}

    def test_request_exception_stale_cache_returns_data(self, tmp_path):
        """Lines 338-345: RadioID fetch exception with stale cache returns stale data."""
        stale_data = {
            "count": 1,
            "results": [{"callsign": "W0OLD", "ts1_static_talkgroups": [9], "ts2_static_talkgroups": []}],
        }
        cache_file = tmp_path / "radioid_MO.json"
        cache_file.write_text(json.dumps(stale_data))
        old_time = time.time() - (800 * 3600)  # 800 hours > 168h cache max age
        os.utime(cache_file, (old_time, old_time))

        with patch("plugsmith.builder.talkgroups.requests.Session") as MockSession:
            MockSession.return_value.get.side_effect = requests.RequestException("timeout")
            MockSession.return_value.headers = {}
            client = RadioIDClient(cache_dir=str(tmp_path), rate_limit=0)
            result = client.fetch_repeater_tgs("MO")

        assert "W0OLD" in result

    def test_empty_callsign_entry_skipped(self, tmp_path):
        """Line 351: RadioID entry with empty callsign is skipped."""
        raw = {
            "count": 2,
            "results": [
                {"callsign": "", "ts1_static_talkgroups": [9], "ts2_static_talkgroups": []},
                {"callsign": "W0ABC", "ts1_static_talkgroups": [9], "ts2_static_talkgroups": []},
            ],
        }
        with patch("plugsmith.builder.talkgroups.requests.Session") as MockSession:
            mock_resp = MagicMock()
            mock_resp.json.return_value = raw
            mock_resp.raise_for_status = MagicMock()
            MockSession.return_value.get.return_value = mock_resp
            MockSession.return_value.headers = {}
            client = RadioIDClient(cache_dir=str(tmp_path), rate_limit=0)
            result = client.fetch_repeater_tgs("MO")

        assert "" not in result
        assert "W0ABC" in result

    def test_clear_cache_missing_file_returns_zero(self, tmp_path):
        """Line 373: clear_cache for state with no file returns 0."""
        with patch("plugsmith.builder.talkgroups.requests.Session") as MockSession:
            MockSession.return_value.headers = {}
            client = RadioIDClient(cache_dir=str(tmp_path))
            count = client.clear_cache("MO")

        assert count == 0


# ---------------------------------------------------------------------------
# models.py — Talkgroup __post_init__ (lines 71-72)
# ---------------------------------------------------------------------------


class TestTalkgroupModel:
    def test_post_init_sets_number_from_tg_id(self):
        """Lines 71-72: __post_init__ sets number=tg_id when number defaults to 0."""
        from plugsmith.builder.models import Talkgroup

        tg = Talkgroup(tg_id=9, name="Local")
        assert tg.number == 9

    def test_post_init_preserves_explicit_number(self):
        """__post_init__ does not overwrite an explicitly set non-zero number."""
        from plugsmith.builder.models import Talkgroup

        tg = Talkgroup(tg_id=9, name="Local", number=42)
        assert tg.number == 42


# ---------------------------------------------------------------------------
# build_config.py — _deep_merge recursive and write_default_config (lines 118, 142-150)
# ---------------------------------------------------------------------------


class TestBuildConfigExtras:
    def test_deep_merge_recursive_nested_dict(self):
        """Line 118: _deep_merge recursively merges nested dicts."""
        from plugsmith.builder.build_config import _deep_merge

        base = {"a": {"x": 1, "y": 2}, "b": 3}
        override = {"a": {"y": 99, "z": 100}}
        _deep_merge(base, override)
        assert base["a"]["x"] == 1    # preserved
        assert base["a"]["y"] == 99   # overridden
        assert base["a"]["z"] == 100  # added
        assert base["b"] == 3         # untouched

    def test_write_default_config_creates_file(self, tmp_path):
        """Lines 142-150: write_default_config creates a valid YAML file."""
        from plugsmith.builder.build_config import write_default_config
        import yaml

        path = str(tmp_path / "config.yaml")
        write_default_config(path)
        assert os.path.exists(path)
        with open(path) as f:
            content = f.read()
        assert "Codeplug Builder" in content
        data = yaml.safe_load(content)
        assert "dmr_id" in data
        assert "anytone_settings" not in data  # excluded from user config
