"""Tests for RadioProfile, RADIO_PROFILES, and DEFAULT_RADIO_PROFILE in tool_discovery."""

import pytest

from plugsmith.tool_discovery import (
    DEFAULT_RADIO_PROFILE,
    RADIO_PROFILES,
    RadioProfile,
)


class TestRadioProfileDataclass:
    def test_has_all_expected_fields(self):
        p = RadioProfile(
            key="test",
            display_name="Test Radio",
            max_channels=1000,
            max_zones=100,
            max_channels_per_zone=50,
            hw_family="generic",
            hw_settings_key=None,
            supported_modes=frozenset({"fm", "dmr"}),
        )
        assert p.key == "test"
        assert p.display_name == "Test Radio"
        assert p.max_channels == 1000
        assert p.max_zones == 100
        assert p.max_channels_per_zone == 50
        assert p.hw_family == "generic"
        assert p.hw_settings_key is None
        assert p.supported_modes == frozenset({"fm", "dmr"})

    def test_hw_settings_key_can_be_string(self):
        p = RadioProfile("k", "Name", 4000, 250, 160, "anytone", "anytone_settings",
                         frozenset({"fm", "dmr"}))
        assert p.hw_settings_key == "anytone_settings"

    def test_supported_modes_is_frozenset(self):
        p = RadioProfile("k", "Name", 1000, 100, 50, "generic", None, frozenset({"fm"}))
        assert isinstance(p.supported_modes, frozenset)


class TestRadioProfilesDict:
    def test_contains_all_known_keys(self):
        expected_keys = {
            "d878uv2", "d878uv", "d868uv", "d578uv",
            "uv390", "md380", "md9600",
            "gd77", "gd77s",
            "d52uv", "dr1801uv",
        }
        assert expected_keys.issubset(set(RADIO_PROFILES.keys()))

    def test_all_entries_are_radio_profiles(self):
        for key, profile in RADIO_PROFILES.items():
            assert isinstance(profile, RadioProfile), f"{key} is not a RadioProfile"

    def test_all_profiles_have_positive_limits(self):
        for key, p in RADIO_PROFILES.items():
            assert p.max_channels > 0, f"{key}.max_channels must be > 0"
            assert p.max_zones > 0, f"{key}.max_zones must be > 0"
            assert p.max_channels_per_zone > 0, f"{key}.max_channels_per_zone must be > 0"

    def test_all_keys_match_profile_key_field(self):
        for key, profile in RADIO_PROFILES.items():
            assert profile.key == key


class TestD878UV2Profile:
    def setup_method(self):
        self.p = RADIO_PROFILES["d878uv2"]

    def test_max_channels(self):
        assert self.p.max_channels == 4000

    def test_max_zones(self):
        assert self.p.max_zones == 250

    def test_max_channels_per_zone(self):
        assert self.p.max_channels_per_zone == 160

    def test_hw_family(self):
        assert self.p.hw_family == "anytone"

    def test_hw_settings_key(self):
        assert self.p.hw_settings_key == "anytone_settings"

    def test_display_name(self):
        assert "AnyTone" in self.p.display_name
        assert "878" in self.p.display_name


class TestGD77Profile:
    def setup_method(self):
        self.p = RADIO_PROFILES["gd77"]

    def test_max_channels(self):
        assert self.p.max_channels == 1024

    def test_max_channels_per_zone(self):
        assert self.p.max_channels_per_zone == 80

    def test_hw_family(self):
        assert self.p.hw_family == "radioddity"

    def test_no_hw_settings_key(self):
        assert self.p.hw_settings_key is None


class TestMD380Profile:
    def setup_method(self):
        self.p = RADIO_PROFILES["md380"]

    def test_max_channels(self):
        assert self.p.max_channels == 1000

    def test_hw_family(self):
        assert self.p.hw_family == "tyt"

    def test_no_hw_settings_key(self):
        assert self.p.hw_settings_key is None


class TestAnytoneFamilyHasSettingsKey:
    """All AnyTone radios should have hw_settings_key set."""

    def test_d878uv_has_settings_key(self):
        assert RADIO_PROFILES["d878uv"].hw_settings_key == "anytone_settings"

    def test_d868uv_has_settings_key(self):
        assert RADIO_PROFILES["d868uv"].hw_settings_key == "anytone_settings"

    def test_d578uv_has_settings_key(self):
        assert RADIO_PROFILES["d578uv"].hw_settings_key == "anytone_settings"


class TestNonAnytoneFamiliesHaveNoSettingsKey:
    """TYT / Radioddity / generic radios have no hw block."""

    @pytest.mark.parametrize("key", ["uv390", "md380", "md9600", "gd77", "gd77s", "d52uv", "dr1801uv"])
    def test_hw_settings_key_is_none(self, key):
        assert RADIO_PROFILES[key].hw_settings_key is None


class TestDefaultRadioProfile:
    def test_is_radio_profile(self):
        assert isinstance(DEFAULT_RADIO_PROFILE, RadioProfile)

    def test_max_channels(self):
        assert DEFAULT_RADIO_PROFILE.max_channels == 4000

    def test_no_hw_settings_key(self):
        assert DEFAULT_RADIO_PROFILE.hw_settings_key is None

    def test_hw_family_generic(self):
        assert DEFAULT_RADIO_PROFILE.hw_family == "generic"

    def test_unknown_key_falls_back_to_default(self):
        result = RADIO_PROFILES.get("totally_unknown_radio_xyz", DEFAULT_RADIO_PROFILE)
        assert result is DEFAULT_RADIO_PROFILE
