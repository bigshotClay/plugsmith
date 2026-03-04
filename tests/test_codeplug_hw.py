"""Tests for generate_codeplug_yaml() — hardware settings routing and core structure."""

import logging
from unittest.mock import patch

import pytest

from plugsmith.builder.codeplug import generate_codeplug_yaml


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _analog_ch(name="Test FM", rx=146.520, tx=146.520, pl=None):
    return {
        "ch_type": "analog",
        "name": name,
        "rx_freq": rx,
        "tx_freq": tx,
        "pl_tone": pl,
        "tsq_tone": None,
    }


def _digital_ch(name="Test DMR", rx=444.100, tx=449.100, cc=1, ts=1, tg=9):
    return {
        "ch_type": "digital",
        "name": name,
        "rx_freq": rx,
        "tx_freq": tx,
        "color_code": cc,
        "time_slot": ts,
        "tg_num": tg,
        "tg_name": "Local",
    }


def _zone(name="Zone", channels=None, tier="home", state="MO"):
    return {"name": name, "tier": tier, "state": state, "channels": channels or []}


def _build(zone_specs=None, dmr_id=3211477, callsign="W0TST", **kwargs):
    return generate_codeplug_yaml(
        zone_specs=zone_specs or [_zone(channels=[_analog_ch()])],
        dmr_id=dmr_id,
        callsign=callsign,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Hardware settings routing
# ---------------------------------------------------------------------------

class TestHardwareSettingsRouting:
    def test_no_hw_settings_no_extra_key(self):
        cp = _build()
        assert "anytone" not in cp["settings"]
        assert "tyt" not in cp["settings"]

    def test_hw_settings_key_none_not_added(self):
        cp = _build(hw_settings={"foo": "bar"}, hw_settings_key=None)
        assert "foo" not in cp["settings"]

    def test_hw_settings_none_not_added(self):
        cp = _build(hw_settings=None, hw_settings_key="anytone_settings")
        assert "anytone" not in cp["settings"]

    def test_anytone_settings_routed_to_anytone_key(self):
        hw = {"vfoModeA": True, "knobMode": "Volume"}
        cp = _build(hw_settings=hw, hw_settings_key="anytone_settings")
        assert cp["settings"]["anytone"] == hw

    def test_tyt_settings_routed_to_tyt_key(self):
        hw = {"someField": 42}
        cp = _build(hw_settings=hw, hw_settings_key="tyt_settings")
        assert cp["settings"]["tyt"] == hw

    def test_generic_settings_key_strips_suffix(self):
        hw = {"x": 1}
        cp = _build(hw_settings=hw, hw_settings_key="custom_settings")
        assert cp["settings"]["custom"] == hw

    def test_hw_settings_empty_dict_not_added(self):
        # {} is falsy in Python — should not insert the key
        cp = _build(hw_settings={}, hw_settings_key="anytone_settings")
        assert "anytone" not in cp["settings"]

    def test_hw_settings_value_stored_verbatim(self):
        hw = {"nested": {"a": 1, "b": [1, 2, 3]}}
        cp = _build(hw_settings=hw, hw_settings_key="anytone_settings")
        assert cp["settings"]["anytone"] == hw


# ---------------------------------------------------------------------------
# Core codeplug structure
# ---------------------------------------------------------------------------

class TestCodeplugStructure:
    def test_returns_dict(self):
        assert isinstance(_build(), dict)

    def test_version_field(self):
        cp = _build()
        assert cp["version"] == "0.12.0"

    def test_settings_contains_callsign(self):
        cp = _build(callsign="W0RRK")
        assert cp["settings"]["defaultID"] == "W0RRK"
        assert cp["settings"]["introLine1"] == "W0RRK"

    def test_radio_id_contains_dmr_id(self):
        cp = _build(dmr_id=3211477)
        assert cp["radioIDs"][0]["dmr"]["number"] == 3211477

    def test_codeplug_has_required_top_level_keys(self):
        cp = _build()
        for key in ("version", "settings", "radioIDs", "contacts", "groupLists", "channels", "zones"):
            assert key in cp, f"Missing key: {key}"


# ---------------------------------------------------------------------------
# Channel generation
# ---------------------------------------------------------------------------

class TestChannelGeneration:
    def test_analog_channel_created(self):
        cp = _build(zone_specs=[_zone(channels=[_analog_ch()])])
        assert len(cp["channels"]) == 1
        assert "analog" in cp["channels"][0]

    def test_digital_channel_created(self):
        cp = _build(zone_specs=[_zone(channels=[_digital_ch()])])
        assert len(cp["channels"]) == 1
        assert "digital" in cp["channels"][0]

    def test_analog_pl_tone_included_when_set(self):
        cp = _build(zone_specs=[_zone(channels=[_analog_ch(pl=100.0)])])
        ch = cp["channels"][0]["analog"]
        assert ch["txTone"] == {"ctcss": 100.0}

    def test_analog_no_pl_tone_when_none(self):
        cp = _build(zone_specs=[_zone(channels=[_analog_ch(pl=None)])])
        ch = cp["channels"][0]["analog"]
        assert "txTone" not in ch

    def test_tsq_tone_included_when_set(self):
        ch_spec = {
            "ch_type": "analog", "name": "FM", "rx_freq": 146.52,
            "tx_freq": 146.52, "pl_tone": None, "tsq_tone": 88.5,
        }
        cp = _build(zone_specs=[_zone(channels=[ch_spec])])
        assert cp["channels"][0]["analog"]["rxTone"] == {"ctcss": 88.5}

    def test_digital_channel_timeslot_format(self):
        cp = _build(zone_specs=[_zone(channels=[_digital_ch(ts=2)])])
        assert cp["channels"][0]["digital"]["timeSlot"] == "TS2"

    def test_digital_channel_color_code(self):
        cp = _build(zone_specs=[_zone(channels=[_digital_ch(cc=3)])])
        assert cp["channels"][0]["digital"]["colorCode"] == 3

    def test_global_deduplication_across_zones(self):
        """Same channel in two zones should create only one channel entry."""
        ch = _analog_ch()
        z1 = _zone("Zone A", [ch])
        z2 = _zone("Zone B", [ch])
        cp = _build(zone_specs=[z1, z2])
        assert len(cp["channels"]) == 1
        assert len(cp["zones"]) == 2

    def test_parrot_and_disconnect_contacts_always_present(self):
        cp = _build(zone_specs=[_zone(channels=[_analog_ch()])])
        tg_nums = {c["dmr"]["number"] for c in cp["contacts"]}
        assert 9998 in tg_nums  # Parrot
        assert 4000 in tg_nums  # Disconnect


# ---------------------------------------------------------------------------
# Zone generation
# ---------------------------------------------------------------------------

class TestZoneGeneration:
    def test_zone_created_for_nonempty_channels(self):
        cp = _build(zone_specs=[_zone("My Zone", [_analog_ch()])])
        assert len(cp["zones"]) == 1
        assert cp["zones"][0]["name"] == "My Zone"

    def test_empty_zone_not_added(self):
        cp = _build(zone_specs=[_zone("Empty", []), _zone("Full", [_analog_ch()])])
        assert len(cp["zones"]) == 1

    def test_zone_id_derived_from_name(self):
        cp = _build(zone_specs=[_zone("MO 2m", [_analog_ch()])])
        assert cp["zones"][0]["id"] == "zone_MO_2m"

    def test_zone_id_replaces_slash(self):
        cp = _build(zone_specs=[_zone("A/B", [_analog_ch()])])
        assert "/" not in cp["zones"][0]["id"]


# ---------------------------------------------------------------------------
# Channel overflow warning
# ---------------------------------------------------------------------------

class TestChannelOverflowWarning:
    def test_warning_logged_when_channel_count_exceeds_max(self, caplog):
        """When more channels are generated than MAX_CHANNELS, a warning is emitted."""
        import plugsmith.builder.codeplug as codeplug_mod

        zone_specs = [_zone("Zone", [_analog_ch(name=f"CH{i}", rx=round(146.0 + i * 0.001, 4),
                                                 tx=round(146.0 + i * 0.001, 4))
                                     for i in range(5)])]
        with patch.object(codeplug_mod, "MAX_CHANNELS", 3):
            with caplog.at_level(logging.WARNING, logger="plugsmith.builder.codeplug"):
                _build(zone_specs=zone_specs)
        assert any("exceeds" in msg.lower() for msg in caplog.messages)


# ---------------------------------------------------------------------------
# Integration: Fusion + D-Star channels in full build
# ---------------------------------------------------------------------------

def _fusion_zone_spec(name="Fusion Zone", freq=146.520, tx=147.120):
    """Zone spec with a Fusion analog channel."""
    return {
        "name": name,
        "tier": "home",
        "state": "MO",
        "channels": [
            {
                "ch_type": "analog",
                "name": "W0FUS Spring Fus",
                "rx_freq": freq,
                "tx_freq": tx,
                "pl_tone": 100.0,
                "tsq_tone": None,
            }
        ],
    }


class TestFusionIntegration:
    def test_fusion_build_produces_analog_channel(self):
        cp = _build(zone_specs=[_fusion_zone_spec()])
        assert len(cp["channels"]) == 1
        assert "analog" in cp["channels"][0]

    def test_fm_and_fusion_same_freq_pl_deduplicated(self):
        """FM analog and Fusion analog on the same freq/tx/pl share a single channel entry."""
        zones = [
            _zone("FM", [_analog_ch(rx=146.520, tx=147.120, pl=100.0)]),
            _fusion_zone_spec(freq=146.520, tx=147.120),  # also pl=100.0 → same dedup key
        ]
        cp = _build(zone_specs=zones)
        # Same freq + tx + pl → deduplicated to 1 channel, referenced in both zones
        assert len(cp["channels"]) == 1
        assert len(cp["zones"]) == 2

    def test_fm_and_fusion_different_pl_are_distinct(self):
        """FM analog (no pl) and Fusion analog (pl=100.0) on same freq are distinct channels."""
        zones = [
            _zone("FM", [_analog_ch(rx=146.520, tx=147.120, pl=None)]),
            _fusion_zone_spec(freq=146.520, tx=147.120),  # pl=100.0 → different dedup key
        ]
        cp = _build(zone_specs=zones)
        assert len(cp["channels"]) == 2

    def test_mixed_fm_fusion_produces_correct_channel_count(self):
        zones = [
            _zone("FM Zone", [_analog_ch(rx=146.520, tx=147.120)]),
            _fusion_zone_spec(freq=146.620, tx=147.220),
        ]
        cp = _build(zone_specs=zones)
        assert len(cp["channels"]) == 2
