"""Tests for validate_modes() in builder/build_config.py."""

import pytest

from plugsmith.builder.build_config import DEFAULT_CONFIG, validate_modes
from plugsmith.tool_discovery import DEFAULT_RADIO_PROFILE, RADIO_PROFILES, RadioProfile


class TestValidateModesPasses:
    def test_fm_dmr_on_d878uv2(self):
        config = {"modes": {"fm": True, "dmr": True}}
        validate_modes(config, RADIO_PROFILES["d878uv2"])  # no exception

    def test_fm_only(self):
        config = {"modes": {"fm": True, "dmr": False}}
        validate_modes(config, RADIO_PROFILES["md380"])  # no exception

    def test_fusion_on_ft3d(self):
        config = {"modes": {"fm": True, "dmr": True, "fusion": True}}
        validate_modes(config, RADIO_PROFILES["ft3d"])  # no exception

    def test_fusion_on_ft5d(self):
        config = {"modes": {"fm": True, "fusion": True}}
        validate_modes(config, RADIO_PROFILES["ft5d"])  # no exception

    def test_dstar_on_id52(self):
        config = {"modes": {"fm": True, "dstar": True}}
        validate_modes(config, RADIO_PROFILES["id52"])  # no exception

    def test_dstar_on_id51(self):
        config = {"modes": {"dstar": True, "fm": True}}
        validate_modes(config, RADIO_PROFILES["id51"])  # no exception

    def test_all_disabled_modes_pass_any_radio(self):
        config = {"modes": {"fm": False, "dmr": False, "dstar": False, "fusion": False}}
        validate_modes(config, RADIO_PROFILES["md380"])  # no exception

    def test_empty_modes_passes(self):
        validate_modes({"modes": {}}, RADIO_PROFILES["d878uv2"])  # no exception

    def test_no_modes_key_passes(self):
        validate_modes({}, RADIO_PROFILES["d878uv2"])  # no exception

    def test_default_config_valid_for_d878uv2(self):
        validate_modes(DEFAULT_CONFIG, RADIO_PROFILES["d878uv2"])  # no exception

    def test_default_config_valid_for_default_profile(self):
        validate_modes(DEFAULT_CONFIG, DEFAULT_RADIO_PROFILE)  # no exception


class TestValidateModesRaises:
    def test_dstar_on_d878uv2_raises(self):
        config = {"modes": {"fm": True, "dmr": True, "dstar": True}}
        with pytest.raises(ValueError, match="dstar"):
            validate_modes(config, RADIO_PROFILES["d878uv2"])

    def test_fusion_on_md380_raises(self):
        config = {"modes": {"fm": True, "dmr": True, "fusion": True}}
        with pytest.raises(ValueError, match="fusion"):
            validate_modes(config, RADIO_PROFILES["md380"])

    def test_fusion_on_d878uv2_raises(self):
        config = {"modes": {"fusion": True}}
        with pytest.raises(ValueError, match="fusion"):
            validate_modes(config, RADIO_PROFILES["d878uv2"])

    def test_dstar_on_gd77_raises(self):
        config = {"modes": {"dstar": True}}
        with pytest.raises(ValueError, match="dstar"):
            validate_modes(config, RADIO_PROFILES["gd77"])

    def test_dstar_on_ft3d_raises(self):
        # FT3D supports fm+dmr+fusion but NOT dstar
        config = {"modes": {"dstar": True}}
        with pytest.raises(ValueError, match="dstar"):
            validate_modes(config, RADIO_PROFILES["ft3d"])

    def test_error_message_contains_radio_key(self):
        config = {"modes": {"fusion": True}}
        with pytest.raises(ValueError) as exc_info:
            validate_modes(config, RADIO_PROFILES["d878uv2"])
        assert "d878uv2" in str(exc_info.value)

    def test_error_message_contains_supported_modes(self):
        config = {"modes": {"fusion": True}}
        with pytest.raises(ValueError) as exc_info:
            validate_modes(config, RADIO_PROFILES["d878uv2"])
        assert "fm" in str(exc_info.value)
        assert "dmr" in str(exc_info.value)


class TestRadioProfileSupportedModesField:
    def test_existing_anytone_profiles_have_fm_dmr(self):
        for key in ("d878uv2", "d878uv", "d868uv", "d578uv"):
            p = RADIO_PROFILES[key]
            assert "fm" in p.supported_modes, f"{key} missing fm"
            assert "dmr" in p.supported_modes, f"{key} missing dmr"

    def test_existing_tyt_profiles_have_fm_dmr(self):
        for key in ("uv390", "md380", "md9600"):
            p = RADIO_PROFILES[key]
            assert "fm" in p.supported_modes
            assert "dmr" in p.supported_modes

    def test_yaesu_ft3d_has_fusion(self):
        assert "fusion" in RADIO_PROFILES["ft3d"].supported_modes

    def test_yaesu_ft5d_has_fusion(self):
        assert "fusion" in RADIO_PROFILES["ft5d"].supported_modes

    def test_icom_id52_has_dstar(self):
        assert "dstar" in RADIO_PROFILES["id52"].supported_modes

    def test_icom_id51_has_dstar(self):
        assert "dstar" in RADIO_PROFILES["id51"].supported_modes

    def test_all_profiles_have_nonempty_supported_modes(self):
        for key, p in RADIO_PROFILES.items():
            assert len(p.supported_modes) > 0, f"{key}.supported_modes is empty"

    def test_supported_modes_is_frozenset(self):
        for key, p in RADIO_PROFILES.items():
            assert isinstance(p.supported_modes, frozenset), f"{key}.supported_modes is not frozenset"

    def test_default_profile_has_fm_dmr(self):
        assert "fm" in DEFAULT_RADIO_PROFILE.supported_modes
        assert "dmr" in DEFAULT_RADIO_PROFILE.supported_modes

    def test_icom_does_not_have_dmr(self):
        # Icom ID-51/52 are D-Star radios, not DMR
        assert "dmr" not in RADIO_PROFILES["id51"].supported_modes
        assert "dmr" not in RADIO_PROFILES["id52"].supported_modes

    def test_anytone_does_not_have_fusion(self):
        assert "fusion" not in RADIO_PROFILES["d878uv2"].supported_modes

    def test_anytone_does_not_have_dstar(self):
        assert "dstar" not in RADIO_PROFILES["d878uv2"].supported_modes
