"""Tests for plugsmith.builder.radio_settings_meta."""

from __future__ import annotations

import pytest

from plugsmith.builder.radio_settings_meta import ANYTONE_SETTINGS, SettingMeta


# ---------------------------------------------------------------------------
# SettingMeta dataclass
# ---------------------------------------------------------------------------


class TestSettingMeta:
    def test_required_fields_present(self):
        m = SettingMeta(
            key="test",
            label="Test",
            stype="bool",
            description="A test setting.",
            ham_preferred="Enabled",
        )
        assert m.key == "test"
        assert m.label == "Test"
        assert m.stype == "bool"
        assert m.description == "A test setting."
        assert m.ham_preferred == "Enabled"
        assert m.warning is None
        assert m.options is None
        assert m.default is None

    def test_warning_field_optional(self):
        m = SettingMeta(
            key="enc",
            label="Enc",
            stype="enum",
            description="Enc desc.",
            ham_preferred="Off",
            warning="Do not use on ham bands.",
            options=["Off", "AES"],
            default="AES",
        )
        assert m.warning == "Do not use on ham bands."
        assert m.options == ["Off", "AES"]
        assert m.default == "AES"


# ---------------------------------------------------------------------------
# ANYTONE_SETTINGS structure
# ---------------------------------------------------------------------------


class TestAnyToneSettingsStructure:
    def test_has_eight_groups(self):
        assert len(ANYTONE_SETTINGS) == 8

    def test_each_entry_is_three_tuple(self):
        for entry in ANYTONE_SETTINGS:
            assert len(entry) == 3
            display, group_key, settings = entry
            assert isinstance(display, str)
            assert isinstance(group_key, str)
            assert isinstance(settings, list)

    def test_group_yaml_keys(self):
        expected_keys = {
            "bootSettings",
            "powerSaveSettings",
            "keySettings",
            "toneSettings",
            "displaySettings",
            "audioSettings",
            "dmrSettings",
            "gpsSettings",
        }
        actual_keys = {g for _, g, _ in ANYTONE_SETTINGS}
        assert actual_keys == expected_keys

    def test_total_setting_count(self):
        total = sum(len(s) for _, _, s in ANYTONE_SETTINGS)
        assert total == 75

    def test_every_group_has_at_least_one_setting(self):
        for display, group_key, settings in ANYTONE_SETTINGS:
            assert len(settings) > 0, f"Group '{display}' ({group_key}) has no settings"

    def test_all_settings_are_setting_meta_instances(self):
        for _, _, settings in ANYTONE_SETTINGS:
            for meta in settings:
                assert isinstance(meta, SettingMeta)


# ---------------------------------------------------------------------------
# Every setting has required content
# ---------------------------------------------------------------------------


class TestSettingContent:
    @pytest.fixture(params=[
        (meta, group_key)
        for _, group_key, settings in ANYTONE_SETTINGS
        for meta in settings
    ])
    def any_setting(self, request):
        return request.param

    def test_non_empty_key(self, any_setting):
        meta, _ = any_setting
        assert meta.key.strip()

    def test_non_empty_label(self, any_setting):
        meta, _ = any_setting
        assert meta.label.strip()

    def test_non_empty_description(self, any_setting):
        meta, _ = any_setting
        assert len(meta.description.strip()) > 10, (
            f"{meta.key}: description too short: {meta.description!r}"
        )

    def test_non_empty_ham_preferred(self, any_setting):
        meta, _ = any_setting
        assert meta.ham_preferred.strip(), f"{meta.key}: ham_preferred is empty"

    def test_valid_stype(self, any_setting):
        meta, _ = any_setting
        assert meta.stype in ("bool", "int", "str", "enum")

    def test_enum_settings_have_options(self, any_setting):
        meta, _ = any_setting
        if meta.stype == "enum":
            assert meta.options and len(meta.options) >= 2, (
                f"{meta.key}: enum setting has no options"
            )

    def test_bool_settings_have_no_options(self, any_setting):
        meta, _ = any_setting
        if meta.stype == "bool":
            assert meta.options is None, (
                f"{meta.key}: bool setting should not have options"
            )


# ---------------------------------------------------------------------------
# Critical ham-radio-specific settings
# ---------------------------------------------------------------------------


def _find_setting(group_key: str, field_key: str) -> SettingMeta:
    for _, gk, settings in ANYTONE_SETTINGS:
        if gk == group_key:
            for meta in settings:
                if meta.key == field_key:
                    return meta
    pytest.fail(f"Setting not found: {group_key}.{field_key}")


class TestCriticalSettings:
    def test_encryption_has_warning(self):
        meta = _find_setting("dmrSettings", "encryption")
        assert meta.warning is not None
        assert "prohibit" in meta.warning.lower() or "illegal" in meta.warning.lower() or "97" in meta.warning

    def test_encryption_warning_mentions_part_97(self):
        meta = _find_setting("dmrSettings", "encryption")
        assert "97" in meta.warning

    def test_encryption_warning_mentions_fcc(self):
        meta = _find_setting("dmrSettings", "encryption")
        assert "FCC" in meta.warning or "CFR" in meta.warning

    def test_encryption_is_enum(self):
        meta = _find_setting("dmrSettings", "encryption")
        assert meta.stype == "enum"
        assert "AES" in meta.options

    def test_send_talker_alias_is_enabled_preferred(self):
        meta = _find_setting("dmrSettings", "sendTalkerAlias")
        assert meta.stype == "bool"
        assert "enabled" in meta.ham_preferred.lower() or "true" in meta.ham_preferred.lower()

    def test_send_talker_alias_preferred_mentions_identification(self):
        meta = _find_setting("dmrSettings", "sendTalkerAlias")
        assert "part 97" in meta.ham_preferred.lower() or "identif" in meta.ham_preferred.lower()

    def test_boot_password_has_warning(self):
        meta = _find_setting("bootSettings", "bootPasswordEnabled")
        assert meta.warning is not None
        assert "disabled" in meta.ham_preferred.lower() or "false" in meta.ham_preferred.lower()

    def test_boot_password_default_false(self):
        meta = _find_setting("bootSettings", "bootPasswordEnabled")
        assert meta.default is False

    def test_p6_short_key_has_warning(self):
        meta = _find_setting("keySettings", "funcKey6Short")
        assert meta.warning is not None
        assert "encryption" in meta.warning.lower() or "Encryption" in meta.warning

    def test_p6_long_key_has_warning(self):
        meta = _find_setting("keySettings", "funcKey6Long")
        assert meta.warning is not None

    def test_dmr_talk_permit_enabled_preferred(self):
        meta = _find_setting("toneSettings", "dmrTalkPermit")
        assert meta.stype == "bool"
        assert meta.default is True

    def test_tot_tone_enabled_preferred(self):
        meta = _find_setting("toneSettings", "tot")
        assert meta.stype == "bool"
        assert meta.default is True

    def test_fan_cooling_has_warning(self):
        meta = _find_setting("powerSaveSettings", "fan")
        assert meta.warning is not None

    def test_fan_default_ptt(self):
        meta = _find_setting("powerSaveSettings", "fan")
        assert meta.default == "PTT"

    def test_pre_wave_delay_has_brandmeister_note(self):
        meta = _find_setting("dmrSettings", "preWaveDelay")
        assert "brandmeister" in meta.description.lower() or "BrandMeister" in meta.description

    def test_sms_format_default_motorola(self):
        meta = _find_setting("dmrSettings", "smsFormat")
        assert meta.default == "Motorola"

    def test_gps_report_position_disabled_preferred(self):
        meta = _find_setting("gpsSettings", "reportPosition")
        assert meta.stype == "bool"
        assert meta.default is False

    def test_reset_default_false(self):
        meta = _find_setting("bootSettings", "reset")
        assert meta.default is False

    def test_encryption_default_aes(self):
        meta = _find_setting("dmrSettings", "encryption")
        assert meta.default == "AES"


# ---------------------------------------------------------------------------
# No duplicate keys within any group
# ---------------------------------------------------------------------------


class TestNoDuplicates:
    def test_no_duplicate_field_keys_within_group(self):
        for display, group_key, settings in ANYTONE_SETTINGS:
            keys = [m.key for m in settings]
            assert len(keys) == len(set(keys)), (
                f"Duplicate keys in group '{display}': {keys}"
            )

    def test_unique_widget_ids_across_all_groups(self):
        """Widget IDs (hw-{group}-{key}) must be unique across the whole metadata."""
        ids = [f"hw-{gk}-{m.key}" for _, gk, settings in ANYTONE_SETTINGS for m in settings]
        assert len(ids) == len(set(ids))
