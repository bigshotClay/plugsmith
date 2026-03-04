"""Tests for scale_config_to_radio() in builder/zones.py."""

import copy

import pytest

from plugsmith.builder.zones import MAX_CHANNELS, scale_config_to_radio
from plugsmith.tool_discovery import DEFAULT_RADIO_PROFILE, RADIO_PROFILES, RadioProfile

GD77 = RADIO_PROFILES["gd77"]       # 1024 channels, scale = 0.256
D878 = RADIO_PROFILES["d878uv2"]    # 4000 channels, scale = 1.0
MD380 = RADIO_PROFILES["md380"]     # 1000 channels

# Expected GD-77 scaled values (scale = 1024/4000 = 0.256)
GD77_SCALE = GD77.max_channels / MAX_CHANNELS


def _scaled(default: int) -> int:
    return max(1, int(default * GD77_SCALE))


class TestScaleDoesNotMutateOriginal:
    def test_original_config_unchanged(self):
        original = {"adjacent_region": {"max_fm_per_state": 30}}
        original_copy = copy.deepcopy(original)
        scale_config_to_radio(original, GD77, {})
        assert original == original_copy

    def test_returns_new_dict(self):
        cfg = {}
        result = scale_config_to_radio(cfg, GD77, {})
        assert result is not cfg


class TestFullScaleD878(object):
    """At scale=1.0 (d878uv2), scaled values equal the defaults."""

    def test_home_fm_scaled_to_default(self):
        result = scale_config_to_radio({}, D878, {})
        assert result["home_region"]["max_fm_per_state"] == 150

    def test_home_dmr_scaled_to_default(self):
        result = scale_config_to_radio({}, D878, {})
        assert result["home_region"]["max_dmr_per_state"] == 100

    def test_adjacent_fm_scaled_to_default(self):
        result = scale_config_to_radio({}, D878, {})
        assert result["adjacent_region"]["max_fm_per_state"] == 30

    def test_adjacent_dmr_freqs_scaled_to_default(self):
        result = scale_config_to_radio({}, D878, {})
        assert result["adjacent_region"]["max_dmr_freqs_per_state"] == 5

    def test_adjacent_tgs_scaled_to_default(self):
        result = scale_config_to_radio({}, D878, {})
        assert result["adjacent_region"]["dmr_tgs_per_freq"] == 3

    def test_shallow_fm_scaled_to_default(self):
        result = scale_config_to_radio({}, D878, {})
        assert result["shallow_region"]["max_fm_freqs"] == 10

    def test_shallow_dmr_scaled_to_default(self):
        result = scale_config_to_radio({}, D878, {})
        assert result["shallow_region"]["max_dmr_freqs"] == 3


class TestGD77ProportionalScaling:
    """At scale=0.256 (gd77), all caps are reduced proportionally."""

    def test_home_fm_scaled(self):
        result = scale_config_to_radio({}, GD77, {})
        assert result["home_region"]["max_fm_per_state"] == _scaled(150)

    def test_home_dmr_scaled(self):
        result = scale_config_to_radio({}, GD77, {})
        assert result["home_region"]["max_dmr_per_state"] == _scaled(100)

    def test_adjacent_fm_scaled(self):
        result = scale_config_to_radio({}, GD77, {})
        assert result["adjacent_region"]["max_fm_per_state"] == _scaled(30)

    def test_adjacent_dmr_freqs_scaled(self):
        result = scale_config_to_radio({}, GD77, {})
        assert result["adjacent_region"]["max_dmr_freqs_per_state"] == _scaled(5)

    def test_adjacent_tgs_scaled(self):
        result = scale_config_to_radio({}, GD77, {})
        assert result["adjacent_region"]["dmr_tgs_per_freq"] == _scaled(3)

    def test_shallow_fm_scaled(self):
        result = scale_config_to_radio({}, GD77, {})
        assert result["shallow_region"]["max_fm_freqs"] == _scaled(10)

    def test_shallow_dmr_scaled(self):
        result = scale_config_to_radio({}, GD77, {})
        assert result["shallow_region"]["max_dmr_freqs"] == _scaled(3)

    def test_all_values_are_at_least_one(self):
        result = scale_config_to_radio({}, GD77, {})
        for section in ("home_region", "adjacent_region", "shallow_region"):
            for key, val in result[section].items():
                if isinstance(val, int):
                    assert val >= 1, f"{section}.{key} must be >= 1"


class TestMinimumCapIsOne:
    """Very small radios floor at 1, never 0."""

    def test_tiny_radio_all_caps_are_one(self):
        tiny = RadioProfile("tiny", "Tiny", 10, 10, 8, "generic", None, frozenset({"fm"}))
        result = scale_config_to_radio({}, tiny, {})
        for section in ("home_region", "adjacent_region", "shallow_region"):
            for key, val in result[section].items():
                if isinstance(val, int):
                    assert val >= 1, f"{section}.{key} = {val}, expected >= 1"


class TestUserCeilingRespected:
    """User-set values lower than scaled result are always kept."""

    def test_user_value_lower_than_scaled_is_kept(self):
        # GD-77 scaled adjacent FM = _scaled(30) = 7; user sets 4 → keep 4
        cfg = {"adjacent_region": {"max_fm_per_state": 4}}
        result = scale_config_to_radio(cfg, GD77, {})
        assert result["adjacent_region"]["max_fm_per_state"] == 4

    def test_user_value_higher_than_scaled_is_capped(self):
        # GD-77 scaled adjacent FM = 7; user sets 20 → cap to 7
        cfg = {"adjacent_region": {"max_fm_per_state": 20}}
        result = scale_config_to_radio(cfg, GD77, {})
        assert result["adjacent_region"]["max_fm_per_state"] == _scaled(30)

    def test_user_value_exactly_at_scaled_is_unchanged(self):
        scaled_val = _scaled(30)
        cfg = {"adjacent_region": {"max_fm_per_state": scaled_val}}
        result = scale_config_to_radio(cfg, GD77, {})
        assert result["adjacent_region"]["max_fm_per_state"] == scaled_val

    def test_full_scale_user_ceiling_respected(self):
        # At d878uv2 (scale=1.0), scaled home FM = 150; user sets 80 → keep 80
        cfg = {"home_region": {"max_fm_per_state": 80}}
        result = scale_config_to_radio(cfg, D878, {})
        assert result["home_region"]["max_fm_per_state"] == 80

    def test_full_scale_user_above_default_is_capped_to_default(self):
        # At d878uv2 (scale=1.0), scaled home FM = 150; user sets 200 → cap to 150
        cfg = {"home_region": {"max_fm_per_state": 200}}
        result = scale_config_to_radio(cfg, D878, {})
        assert result["home_region"]["max_fm_per_state"] == 150


class TestMissingSections:
    """Missing config sections are created automatically."""

    def test_missing_home_region_section_created(self):
        result = scale_config_to_radio({}, GD77, {})
        assert "home_region" in result

    def test_missing_adjacent_region_section_created(self):
        result = scale_config_to_radio({}, GD77, {})
        assert "adjacent_region" in result

    def test_missing_shallow_region_section_created(self):
        result = scale_config_to_radio({}, GD77, {})
        assert "shallow_region" in result

    def test_existing_unrelated_config_keys_preserved(self):
        cfg = {"dmr_id": 12345, "callsign": "W0TST"}
        result = scale_config_to_radio(cfg, GD77, {})
        assert result["dmr_id"] == 12345
        assert result["callsign"] == "W0TST"

    def test_existing_unrelated_section_keys_preserved(self):
        cfg = {"home_region": {"dmr_talkgroups_per_repeater": 7}}
        result = scale_config_to_radio(cfg, GD77, {})
        assert result["home_region"]["dmr_talkgroups_per_repeater"] == 7


class TestFusionScaling:
    """Fusion caps are scaled alongside FM and DMR."""

    def test_home_fusion_scaled_d878uv2(self):
        result = scale_config_to_radio({}, D878, {})
        assert result["home_region"]["max_fusion_per_state"] == 50

    def test_adjacent_fusion_scaled_d878uv2(self):
        result = scale_config_to_radio({}, D878, {})
        assert result["adjacent_region"]["max_fusion_per_state"] == 10

    def test_shallow_fusion_scaled_d878uv2(self):
        result = scale_config_to_radio({}, D878, {})
        assert result["shallow_region"]["max_fusion_freqs"] == 3

    def test_home_fusion_scaled_gd77(self):
        result = scale_config_to_radio({}, GD77, {})
        assert result["home_region"]["max_fusion_per_state"] == _scaled(50)

    def test_fusion_cap_at_least_one_for_tiny_radio(self):
        tiny = RadioProfile("tiny", "Tiny", 10, 10, 8, "generic", None, frozenset({"fm"}))
        result = scale_config_to_radio({}, tiny, {})
        assert result["home_region"]["max_fusion_per_state"] >= 1
        assert result["adjacent_region"]["max_fusion_per_state"] >= 1
        assert result["shallow_region"]["max_fusion_freqs"] >= 1


class TestEstimateChannelsUncapped:
    """estimate_channels_uncapped() accounts for Fusion."""

    def test_fusion_counted_when_enabled(self):
        from plugsmith.builder.zones import estimate_channels_uncapped
        from tests.conftest import make_repeater

        r = make_repeater(is_fm=False, is_fusion=True, state_abbr="MO")
        config = {"modes": {"fm": False, "dmr": False, "fusion": True},
                  "home_region": {"dmr_talkgroups_per_repeater": 7},
                  "simplex": {"channels": []}}
        count = estimate_channels_uncapped([r], {"MO": "home"}, config)
        assert count == 1

    def test_fusion_not_counted_when_disabled(self):
        from plugsmith.builder.zones import estimate_channels_uncapped
        from tests.conftest import make_repeater

        r = make_repeater(is_fm=False, is_fusion=True, state_abbr="MO")
        config = {"modes": {"fm": False, "dmr": False, "fusion": False},
                  "home_region": {"dmr_talkgroups_per_repeater": 7},
                  "simplex": {"channels": []}}
        count = estimate_channels_uncapped([r], {"MO": "home"}, config)
        assert count == 0
