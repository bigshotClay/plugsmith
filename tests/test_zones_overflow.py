"""Tests for _add_zone_with_overflow() and organize_zones_tiered() new params."""

import logging
from unittest.mock import patch

import pytest

from plugsmith.builder.zones import (
    MAX_CHANNELS,
    MAX_CHANNELS_PER_ZONE,
    _add_zone_with_overflow,
    organize_zones_tiered,
)
from tests.conftest import make_repeater


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ch(n: int) -> dict:
    """Return a minimal analog channel dict, unique by index."""
    return {
        "ch_type": "analog",
        "name": f"CH{n:04d}",
        "rx_freq": round(146.000 + n * 0.005, 4),
        "tx_freq": round(146.000 + n * 0.005, 4),
        "pl_tone": None,
        "tsq_tone": None,
    }


def _make_channels(n: int) -> list[dict]:
    return [_ch(i) for i in range(n)]


# ---------------------------------------------------------------------------
# _add_zone_with_overflow
# ---------------------------------------------------------------------------

class TestAddZoneWithOverflow:
    def test_empty_channels_adds_nothing(self):
        specs: list[dict] = []
        _add_zone_with_overflow(specs, "Test", [], "home", "MO")
        assert specs == []

    def test_channels_below_limit_creates_single_zone(self):
        specs: list[dict] = []
        _add_zone_with_overflow(specs, "Test", _make_channels(5), "home", "MO", max_per_zone=10)
        assert len(specs) == 1
        assert len(specs[0]["channels"]) == 5

    def test_channels_at_limit_creates_single_zone(self):
        specs: list[dict] = []
        _add_zone_with_overflow(specs, "Test", _make_channels(10), "home", "MO", max_per_zone=10)
        assert len(specs) == 1

    def test_channels_over_limit_splits_into_multiple_zones(self):
        specs: list[dict] = []
        _add_zone_with_overflow(specs, "Test", _make_channels(11), "home", "MO", max_per_zone=10)
        assert len(specs) == 2
        assert len(specs[0]["channels"]) == 10
        assert len(specs[1]["channels"]) == 1

    def test_three_way_split(self):
        specs: list[dict] = []
        _add_zone_with_overflow(specs, "Base", _make_channels(25), "home", "MO", max_per_zone=10)
        assert len(specs) == 3
        assert len(specs[0]["channels"]) == 10
        assert len(specs[1]["channels"]) == 10
        assert len(specs[2]["channels"]) == 5

    def test_first_zone_has_base_name(self):
        specs: list[dict] = []
        _add_zone_with_overflow(specs, "MO 2m", _make_channels(5), "home", "MO", max_per_zone=10)
        assert specs[0]["name"] == "MO 2m"

    def test_overflow_zones_get_numeric_suffix(self):
        specs: list[dict] = []
        _add_zone_with_overflow(specs, "State", _make_channels(21), "home", "MO", max_per_zone=10)
        assert specs[0]["name"] == "State"
        assert specs[1]["name"] == "State 2"
        assert specs[2]["name"] == "State 3"

    def test_long_base_name_truncated_to_16(self):
        specs: list[dict] = []
        _add_zone_with_overflow(specs, "A" * 30, _make_channels(3), "home", "MO", max_per_zone=10)
        assert len(specs[0]["name"]) <= 16

    def test_overflow_zone_name_leaves_room_for_suffix(self):
        specs: list[dict] = []
        long_name = "B" * 30
        _add_zone_with_overflow(specs, long_name, _make_channels(11), "home", "MO", max_per_zone=10)
        assert len(specs[1]["name"]) <= 16
        assert specs[1]["name"].endswith(" 2")

    def test_zone_metadata_fields_set(self):
        specs: list[dict] = []
        _add_zone_with_overflow(specs, "Test", _make_channels(1), "adjacent", "KS", max_per_zone=10)
        assert specs[0]["tier"] == "adjacent"
        assert specs[0]["state"] == "KS"

    def test_default_max_per_zone_is_module_constant(self):
        """When max_per_zone omitted, uses MAX_CHANNELS_PER_ZONE."""
        specs: list[dict] = []
        _add_zone_with_overflow(specs, "Zone", _make_channels(MAX_CHANNELS_PER_ZONE), "home", "MO")
        assert len(specs) == 1

    def test_small_max_per_zone_respected(self):
        specs: list[dict] = []
        _add_zone_with_overflow(specs, "Zone", _make_channels(16), "home", "MO", max_per_zone=5)
        # 16 channels at 5/zone → 4 zones (5,5,5,1)
        assert len(specs) == 4


# ---------------------------------------------------------------------------
# organize_zones_tiered — max_channels_per_zone param
# ---------------------------------------------------------------------------

class TestOrganizeZonesTieredMaxPerZone:
    """organize_zones_tiered passes effective_zone_max to _add_zone_with_overflow."""

    def _build_with_home_repeaters(self, count: int, max_per_zone: int) -> list[dict]:
        """Build zone specs for `count` FM repeaters in MO home state."""
        repeaters = [
            make_repeater(
                callsign=f"W{i:04d}",
                frequency=round(146.000 + i * 0.025, 3),
                input_freq=round(146.000 + i * 0.025 + 0.6, 3),
                state_abbr="MO",
                distance=float(i * 5),
            )
            for i in range(count)
        ]
        config = {
            "home_state": "MO",
            "home_region": {"max_fm_per_state": count, "max_dmr_per_state": 0},
            "adjacent_region": {"max_fm_per_state": 0, "max_dmr_freqs_per_state": 0, "dmr_tgs_per_freq": 0},
            "shallow_region": {"max_fm_freqs": 0, "max_dmr_freqs": 0},
            "simplex": {"channels": []},
        }
        state_tiers = {"MO": "home"}
        return organize_zones_tiered(
            repeaters=repeaters,
            state_tiers=state_tiers,
            ctcss_map={},
            input_freq_map={},
            config=config,
            state_tg_map={},
            max_channels_per_zone=max_per_zone,
        )

    def test_zones_do_not_exceed_max_channels_per_zone(self):
        specs = self._build_with_home_repeaters(count=30, max_per_zone=5)
        for zs in specs:
            assert len(zs["channels"]) <= 5, (
                f"Zone '{zs['name']}' has {len(zs['channels'])} channels, expected <= 5"
            )

    def test_effective_zone_max_uses_smaller_of_module_and_radio_limit(self):
        # Module constant is 160; radio limit 80 → effective should be 80
        specs = self._build_with_home_repeaters(count=100, max_per_zone=80)
        for zs in specs:
            assert len(zs["channels"]) <= 80

    def test_default_max_channels_per_zone_is_module_constant(self):
        specs = self._build_with_home_repeaters(count=5, max_per_zone=MAX_CHANNELS_PER_ZONE)
        # With 5 channels and 160 per zone → single zone per band
        zone_sizes = [len(zs["channels"]) for zs in specs]
        assert all(s <= MAX_CHANNELS_PER_ZONE for s in zone_sizes)


# ---------------------------------------------------------------------------
# organize_zones_tiered — max_channels warning
# ---------------------------------------------------------------------------

class TestOrganizeZonesTieredMaxChannelsWarning:
    def test_warning_logged_when_channels_exceed_max(self, caplog):
        """When total channels exceed max_channels, a warning is emitted."""
        # Create more repeaters than max_channels allows
        repeaters = [
            make_repeater(
                callsign=f"W{i:04d}",
                frequency=round(146.000 + i * 0.025, 3),
                input_freq=round(146.600 + i * 0.025, 3),
                state_abbr="MO",
                distance=float(i),
            )
            for i in range(10)
        ]
        config = {
            "home_state": "MO",
            "home_region": {"max_fm_per_state": 10, "max_dmr_per_state": 0},
            "adjacent_region": {"max_fm_per_state": 0, "max_dmr_freqs_per_state": 0, "dmr_tgs_per_freq": 0},
            "shallow_region": {"max_fm_freqs": 0, "max_dmr_freqs": 0},
            "simplex": {"channels": []},
        }
        with caplog.at_level(logging.WARNING, logger="plugsmith.builder.zones"):
            organize_zones_tiered(
                repeaters=repeaters,
                state_tiers={"MO": "home"},
                ctcss_map={},
                input_freq_map={},
                config=config,
                state_tg_map={},
                max_channels=5,  # less than the 10 channels we'll generate
            )
        assert any("exceeds" in msg.lower() for msg in caplog.messages)

    def test_no_warning_when_within_limit(self, caplog):
        repeaters = [
            make_repeater(
                callsign="W0ABC",
                frequency=146.520,
                input_freq=147.120,
                state_abbr="MO",
            )
        ]
        config = {
            "home_state": "MO",
            "home_region": {"max_fm_per_state": 1, "max_dmr_per_state": 0},
            "adjacent_region": {"max_fm_per_state": 0, "max_dmr_freqs_per_state": 0, "dmr_tgs_per_freq": 0},
            "shallow_region": {"max_fm_freqs": 0, "max_dmr_freqs": 0},
            "simplex": {"channels": []},
        }
        with caplog.at_level(logging.WARNING, logger="plugsmith.builder.zones"):
            organize_zones_tiered(
                repeaters=repeaters,
                state_tiers={"MO": "home"},
                ctcss_map={},
                input_freq_map={},
                config=config,
                state_tg_map={},
                max_channels=MAX_CHANNELS,
            )
        assert not any("exceeds" in msg.lower() for msg in caplog.messages)
