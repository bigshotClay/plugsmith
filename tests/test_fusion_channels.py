"""Tests for Fusion channel builders in builder/zones.py."""

import pytest

from plugsmith.builder.zones import (
    _fusion_channels_for_state,
    adjacent_state_channels,
    home_state_channels,
    organize_zones_tiered,
    shallow_state_channels,
)
from tests.conftest import make_repeater


def _fusion_rpt(callsign="W0FUS", freq=146.520, tx=147.120, distance=50.0, state="MO"):
    return make_repeater(
        callsign=callsign,
        frequency=freq,
        input_freq=tx,
        state_abbr=state,
        is_fm=False,
        is_fusion=True,
        pl_tone=100.0,
        distance=distance,
    )


def _fm_rpt(callsign="W0FM", freq=146.600, tx=147.200, distance=60.0, state="MO"):
    return make_repeater(
        callsign=callsign,
        frequency=freq,
        input_freq=tx,
        state_abbr=state,
        is_fm=True,
        is_fusion=False,
        distance=distance,
    )


class TestFusionChannelsForState:
    def test_produces_one_channel_per_repeater(self):
        rpts = [_fusion_rpt(f"W0F{i}") for i in range(3)]
        channels = _fusion_channels_for_state(rpts, max_count=None)
        assert len(channels) == 3

    def test_channel_type_is_analog(self):
        rpts = [_fusion_rpt()]
        channels = _fusion_channels_for_state(rpts, max_count=None)
        assert channels[0]["ch_type"] == "analog"

    def test_channel_has_correct_rx_freq(self):
        r = _fusion_rpt(freq=146.520, tx=147.120)
        channels = _fusion_channels_for_state([r], max_count=None)
        assert channels[0]["rx_freq"] == 146.520

    def test_channel_has_correct_tx_freq(self):
        r = _fusion_rpt(freq=146.520, tx=147.120)
        channels = _fusion_channels_for_state([r], max_count=None)
        assert channels[0]["tx_freq"] == 147.120

    def test_max_count_limit_respected(self):
        rpts = [_fusion_rpt(f"W0F{i}") for i in range(10)]
        channels = _fusion_channels_for_state(rpts, max_count=3)
        assert len(channels) == 3

    def test_non_fusion_repeaters_excluded(self):
        fm = _fm_rpt()
        fusion = _fusion_rpt()
        channels = _fusion_channels_for_state([fm, fusion], max_count=None)
        assert len(channels) == 1

    def test_channels_sorted_by_distance(self):
        far = _fusion_rpt("WFAR", distance=200.0)
        near = _fusion_rpt("WNEAR", distance=10.0)
        channels = _fusion_channels_for_state([far, near], max_count=1)
        assert "WNEAR" in channels[0]["name"]

    def test_channel_name_contains_fusion_suffix(self):
        r = _fusion_rpt(callsign="W0ABC")
        channels = _fusion_channels_for_state([r], max_count=None)
        assert "Fus" in channels[0]["name"] or "W0ABC" in channels[0]["name"]

    def test_channel_name_max_16_chars(self):
        r = _fusion_rpt(callsign="W0LONGCALL")
        channels = _fusion_channels_for_state([r], max_count=None)
        assert len(channels[0]["name"]) <= 16

    def test_empty_returns_empty(self):
        channels = _fusion_channels_for_state([], max_count=None)
        assert channels == []


class TestHomeStateChannelsFusion:
    def _config_fusion_enabled(self, max_fusion=50):
        return {
            "modes": {"fm": True, "dmr": False, "fusion": True},
            "home_region": {"max_fm_per_state": 50, "max_fusion_per_state": max_fusion},
        }

    def _config_fusion_disabled(self):
        return {
            "modes": {"fm": True, "dmr": False, "fusion": False},
            "home_region": {"max_fm_per_state": 50},
        }

    def test_fusion_channels_included_when_enabled(self):
        r = _fusion_rpt()
        channels = home_state_channels("MO", [r], self._config_fusion_enabled(), {})
        assert any(ch["ch_type"] == "analog" for ch in channels)
        assert len(channels) == 1

    def test_fusion_channels_excluded_when_disabled(self):
        r = _fusion_rpt()
        channels = home_state_channels("MO", [r], self._config_fusion_disabled(), {})
        assert channels == []

    def test_fusion_max_per_state_respected(self):
        rpts = [_fusion_rpt(f"W0F{i}", freq=round(146.5 + i * 0.1, 1),
                             tx=round(147.1 + i * 0.1, 1)) for i in range(10)]
        channels = home_state_channels("MO", rpts, self._config_fusion_enabled(max_fusion=3), {})
        assert len([ch for ch in channels if ch["ch_type"] == "analog"]) == 3

    def test_fusion_and_fm_both_included(self):
        fm = _fm_rpt()
        fusion = _fusion_rpt(freq=146.520, tx=147.120)
        config = {
            "modes": {"fm": True, "dmr": False, "fusion": True},
            "home_region": {"max_fm_per_state": 50, "max_fusion_per_state": 50},
        }
        channels = home_state_channels("MO", [fm, fusion], config, {})
        assert len(channels) == 2


class TestAdjacentStateChannelsFusion:
    def _config(self, fusion=True):
        return {
            "modes": {"fm": True, "dmr": False, "fusion": fusion},
            "adjacent_region": {
                "max_fm_per_state": 5,
                "max_dmr_freqs_per_state": 0,
                "dmr_tgs_per_freq": 0,
                "max_fusion_per_state": 5,
            },
        }

    def test_fusion_channels_included_when_enabled(self):
        r = _fusion_rpt()
        channels = adjacent_state_channels("IL", [r], {}, {}, self._config(fusion=True))
        assert any(ch["ch_type"] == "analog" for ch in channels)

    def test_fusion_channels_excluded_when_disabled(self):
        r = _fusion_rpt()
        channels = adjacent_state_channels("IL", [r], {}, {}, self._config(fusion=False))
        assert all(ch["ch_type"] != "analog" or ch.get("pl_tone") is not None
                   for ch in channels)  # no fusion channels
        assert not any("Fus" in ch["name"] for ch in channels)

    def test_fusion_max_per_state_respected(self):
        rpts = [_fusion_rpt(f"W0F{i}", freq=round(146.5 + i * 0.1, 1),
                             tx=round(147.1 + i * 0.1, 1)) for i in range(10)]
        config = {
            "modes": {"fm": False, "dmr": False, "fusion": True},
            "adjacent_region": {
                "max_fm_per_state": 0,
                "max_dmr_freqs_per_state": 0,
                "dmr_tgs_per_freq": 0,
                "max_fusion_per_state": 2,
            },
        }
        channels = adjacent_state_channels("IL", rpts, {}, {}, config)
        assert len(channels) == 2


class TestShallowStateChannelsFusion:
    def _config(self, fusion=True):
        return {
            "modes": {"fm": False, "dmr": False, "fusion": fusion},
            "shallow_region": {"max_fm_freqs": 0, "max_dmr_freqs": 0, "max_fusion_freqs": 3},
        }

    def test_fusion_channels_included_when_enabled(self):
        r = _fusion_rpt()
        channels = shallow_state_channels("KS", [r], {}, {}, self._config(fusion=True))
        assert any(ch["ch_type"] == "analog" for ch in channels)

    def test_fusion_channels_excluded_when_disabled(self):
        r = _fusion_rpt()
        channels = shallow_state_channels("KS", [r], {}, {}, self._config(fusion=False))
        assert channels == []

    def test_fusion_freq_limit_respected(self):
        rpts = [_fusion_rpt(f"W0F{i}", freq=round(146.5 + i * 0.1, 1),
                             tx=round(147.1 + i * 0.1, 1)) for i in range(10)]
        channels = shallow_state_channels("KS", rpts, {}, {}, self._config(fusion=True))
        assert len(channels) == 3  # max_fusion_freqs=3

    def test_fusion_dedup_by_frequency(self):
        r1 = _fusion_rpt(freq=146.520, tx=147.120)
        r2 = _fusion_rpt(freq=146.520, tx=147.120)
        channels = shallow_state_channels("KS", [r1, r2], {}, {}, self._config(fusion=True))
        assert len([ch for ch in channels if ch["ch_type"] == "analog"]) == 1


class TestOrganizeZonesTieredFusion:
    def _run(self, repeaters, config, state_tiers=None):
        if state_tiers is None:
            state_tiers = {"MO": "home"}
        return organize_zones_tiered(
            repeaters=repeaters,
            state_tiers=state_tiers,
            ctcss_map={},
            input_freq_map={},
            config=config,
            state_tg_map={},
        )

    def test_fusion_channels_appear_in_home_zone(self):
        r = _fusion_rpt(freq=146.520, tx=147.120)
        config = {
            "home_state": "MO",
            "modes": {"fm": False, "dmr": False, "fusion": True},
            "home_region": {"max_fm_per_state": 0, "max_dmr_per_state": 0, "max_fusion_per_state": 50},
            "adjacent_region": {},
            "shallow_region": {},
            "simplex": {"channels": []},
        }
        zones = self._run([r], config)
        all_channels = [ch for z in zones for ch in z["channels"]]
        assert any(ch["ch_type"] == "analog" for ch in all_channels)

    def test_no_fusion_when_disabled(self):
        r = _fusion_rpt()
        config = {
            "home_state": "MO",
            "modes": {"fm": False, "dmr": False, "fusion": False},
            "home_region": {"max_fm_per_state": 0, "max_dmr_per_state": 0},
            "adjacent_region": {},
            "shallow_region": {},
            "simplex": {"channels": []},
        }
        zones = self._run([r], config)
        all_channels = [ch for z in zones for ch in z["channels"]]
        assert all_channels == []
