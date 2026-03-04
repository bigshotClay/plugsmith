"""Tests for D-Star channel builders in builder/zones.py and codeplug.py."""

import pytest

from plugsmith.builder.codeplug import generate_codeplug_yaml
from plugsmith.builder.zones import (
    _dstar_channels_for_state,
    adjacent_state_channels,
    home_state_channels,
    shallow_state_channels,
)
from tests.conftest import make_repeater


def _dstar_rpt(callsign="W0DST", freq=146.520, tx=147.120, distance=50.0, state="MO"):
    return make_repeater(
        callsign=callsign,
        frequency=freq,
        input_freq=tx,
        state_abbr=state,
        is_fm=False,
        is_dstar=True,
        pl_tone=None,
        distance=distance,
    )


def _fm_rpt(callsign="W0FM", freq=146.600, tx=147.200, distance=60.0):
    return make_repeater(
        callsign=callsign,
        frequency=freq,
        input_freq=tx,
        is_fm=True,
        distance=distance,
    )


class TestDStarChannelsForState:
    def test_produces_one_channel_per_repeater(self):
        rpts = [_dstar_rpt(f"W0D{i}") for i in range(3)]
        channels = _dstar_channels_for_state(rpts, max_count=None)
        assert len(channels) == 3

    def test_channel_type_is_dstar(self):
        rpts = [_dstar_rpt()]
        channels = _dstar_channels_for_state(rpts, max_count=None)
        assert channels[0]["ch_type"] == "dstar"

    def test_channel_has_correct_rx_freq(self):
        r = _dstar_rpt(freq=146.520, tx=147.120)
        channels = _dstar_channels_for_state([r], max_count=None)
        assert channels[0]["rx_freq"] == 146.520

    def test_channel_has_correct_tx_freq(self):
        r = _dstar_rpt(freq=146.520, tx=147.120)
        channels = _dstar_channels_for_state([r], max_count=None)
        assert channels[0]["tx_freq"] == 147.120

    def test_max_count_limit_respected(self):
        rpts = [_dstar_rpt(f"W0D{i}") for i in range(10)]
        channels = _dstar_channels_for_state(rpts, max_count=3)
        assert len(channels) == 3

    def test_non_dstar_repeaters_excluded(self):
        fm = _fm_rpt()
        dstar = _dstar_rpt()
        channels = _dstar_channels_for_state([fm, dstar], max_count=None)
        assert len(channels) == 1

    def test_channels_sorted_by_distance(self):
        far = _dstar_rpt("WFAR", distance=200.0)
        near = _dstar_rpt("WNEAR", distance=10.0)
        channels = _dstar_channels_for_state([far, near], max_count=1)
        assert "WNEAR" in channels[0]["name"]

    def test_channel_name_contains_dstar_suffix(self):
        r = _dstar_rpt(callsign="W0ABC")
        channels = _dstar_channels_for_state([r], max_count=None)
        assert "DS" in channels[0]["name"] or "W0ABC" in channels[0]["name"]

    def test_channel_name_max_16_chars(self):
        r = _dstar_rpt(callsign="W0LONGCALL")
        channels = _dstar_channels_for_state([r], max_count=None)
        assert len(channels[0]["name"]) <= 16

    def test_empty_returns_empty(self):
        channels = _dstar_channels_for_state([], max_count=None)
        assert channels == []


class TestHomeStateChannelsDStar:
    def _config_dstar_enabled(self, max_dstar=30):
        return {
            "modes": {"fm": True, "dmr": False, "dstar": True},
            "home_region": {"max_fm_per_state": 50, "max_dstar_per_state": max_dstar},
        }

    def _config_dstar_disabled(self):
        return {
            "modes": {"fm": True, "dmr": False, "dstar": False},
            "home_region": {"max_fm_per_state": 50},
        }

    def test_dstar_channels_included_when_enabled(self):
        r = _dstar_rpt()
        channels = home_state_channels("MO", [r], self._config_dstar_enabled(), {})
        assert any(ch["ch_type"] == "dstar" for ch in channels)

    def test_dstar_channels_excluded_when_disabled(self):
        r = _dstar_rpt()
        channels = home_state_channels("MO", [r], self._config_dstar_disabled(), {})
        assert not any(ch["ch_type"] == "dstar" for ch in channels)
        assert channels == []

    def test_dstar_max_per_state_respected(self):
        rpts = [_dstar_rpt(f"W0D{i}", freq=round(146.5 + i * 0.1, 1),
                            tx=round(147.1 + i * 0.1, 1)) for i in range(10)]
        channels = home_state_channels("MO", rpts, self._config_dstar_enabled(max_dstar=2), {})
        assert len([ch for ch in channels if ch["ch_type"] == "dstar"]) == 2

    def test_dstar_and_fm_both_included(self):
        fm = _fm_rpt()
        dstar = _dstar_rpt(freq=146.520, tx=147.120)
        config = {
            "modes": {"fm": True, "dmr": False, "dstar": True},
            "home_region": {"max_fm_per_state": 50, "max_dstar_per_state": 30},
        }
        channels = home_state_channels("MO", [fm, dstar], config, {})
        assert any(ch["ch_type"] == "analog" for ch in channels)
        assert any(ch["ch_type"] == "dstar" for ch in channels)


class TestAdjacentStateChannelsDStar:
    def _config(self, dstar=True):
        return {
            "modes": {"fm": False, "dmr": False, "dstar": dstar},
            "adjacent_region": {
                "max_fm_per_state": 0,
                "max_dmr_freqs_per_state": 0,
                "dmr_tgs_per_freq": 0,
                "max_dstar_per_state": 5,
            },
        }

    def test_dstar_included_when_enabled(self):
        r = _dstar_rpt()
        channels = adjacent_state_channels("IL", [r], {}, {}, self._config(dstar=True))
        assert any(ch["ch_type"] == "dstar" for ch in channels)

    def test_dstar_excluded_when_disabled(self):
        r = _dstar_rpt()
        channels = adjacent_state_channels("IL", [r], {}, {}, self._config(dstar=False))
        assert not any(ch["ch_type"] == "dstar" for ch in channels)

    def test_max_dstar_per_state_respected(self):
        rpts = [_dstar_rpt(f"W0D{i}", freq=round(146.5 + i * 0.1, 1),
                            tx=round(147.1 + i * 0.1, 1)) for i in range(10)]
        config = {
            "modes": {"fm": False, "dmr": False, "dstar": True},
            "adjacent_region": {
                "max_fm_per_state": 0,
                "max_dmr_freqs_per_state": 0,
                "dmr_tgs_per_freq": 0,
                "max_dstar_per_state": 2,
            },
        }
        channels = adjacent_state_channels("IL", rpts, {}, {}, config)
        assert len(channels) == 2


class TestShallowStateChannelsDStar:
    def _config(self, dstar=True):
        return {
            "modes": {"fm": False, "dmr": False, "dstar": dstar},
            "shallow_region": {"max_fm_freqs": 0, "max_dmr_freqs": 0, "max_dstar_freqs": 2},
        }

    def test_dstar_included_when_enabled(self):
        r = _dstar_rpt()
        channels = shallow_state_channels("KS", [r], {}, {}, self._config(dstar=True))
        assert any(ch["ch_type"] == "dstar" for ch in channels)

    def test_dstar_excluded_when_disabled(self):
        r = _dstar_rpt()
        channels = shallow_state_channels("KS", [r], {}, {}, self._config(dstar=False))
        assert not any(ch["ch_type"] == "dstar" for ch in channels)

    def test_dstar_freq_limit_respected(self):
        rpts = [_dstar_rpt(f"W0D{i}", freq=round(146.5 + i * 0.1, 1),
                            tx=round(147.1 + i * 0.1, 1)) for i in range(10)]
        channels = shallow_state_channels("KS", rpts, {}, {}, self._config(dstar=True))
        assert len(channels) == 2  # max_dstar_freqs=2

    def test_dstar_dedup_by_frequency(self):
        r1 = _dstar_rpt("W0A", freq=146.520, tx=147.120)
        r2 = _dstar_rpt("W0B", freq=146.520, tx=147.120)
        channels = shallow_state_channels("KS", [r1, r2], {}, {}, self._config(dstar=True))
        assert len([ch for ch in channels if ch["ch_type"] == "dstar"]) == 1


class TestDStarCodeplugYAML:
    def _dstar_zone(self, freq=146.520, tx=147.120):
        return {
            "name": "DStar Zone",
            "tier": "home",
            "state": "MO",
            "channels": [
                {
                    "ch_type": "dstar",
                    "name": "W0DST Spring DS",
                    "rx_freq": freq,
                    "tx_freq": tx,
                }
            ],
        }

    def test_dstar_channel_has_dstar_key(self):
        cp = generate_codeplug_yaml(
            zone_specs=[self._dstar_zone()],
            dmr_id=3211477,
            callsign="W0TST",
        )
        assert len(cp["channels"]) == 1
        assert "dstar" in cp["channels"][0]

    def test_dstar_channel_has_correct_freqs(self):
        cp = generate_codeplug_yaml(
            zone_specs=[self._dstar_zone(freq=146.520, tx=147.120)],
            dmr_id=3211477,
            callsign="W0TST",
        )
        ch = cp["channels"][0]["dstar"]
        assert ch["rxFrequency"] == 146.520
        assert ch["txFrequency"] == 147.120

    def test_dstar_channel_has_required_fields(self):
        cp = generate_codeplug_yaml(
            zone_specs=[self._dstar_zone()],
            dmr_id=3211477,
            callsign="W0TST",
        )
        ch = cp["channels"][0]["dstar"]
        for field in ("id", "name", "rxFrequency", "txFrequency", "power", "admit"):
            assert field in ch, f"Missing field: {field}"

    def test_dstar_channels_deduplicated(self):
        zone1 = self._dstar_zone(freq=146.520, tx=147.120)
        zone2 = self._dstar_zone(freq=146.520, tx=147.120)
        cp = generate_codeplug_yaml(
            zone_specs=[zone1, zone2],
            dmr_id=3211477,
            callsign="W0TST",
        )
        # Same freq/tx → deduplicated to single channel entry
        assert len(cp["channels"]) == 1
        assert len(cp["zones"]) == 2  # but still two zones referencing it

    def test_dstar_different_freqs_not_deduplicated(self):
        zone1 = self._dstar_zone(freq=146.520, tx=147.120)
        zone2 = self._dstar_zone(freq=444.100, tx=449.100)
        cp = generate_codeplug_yaml(
            zone_specs=[zone1, zone2],
            dmr_id=3211477,
            callsign="W0TST",
        )
        assert len(cp["channels"]) == 2

    def test_zone_includes_dstar_channel_id(self):
        cp = generate_codeplug_yaml(
            zone_specs=[self._dstar_zone()],
            dmr_id=3211477,
            callsign="W0TST",
        )
        ch_id = cp["channels"][0]["dstar"]["id"]
        assert ch_id in cp["zones"][0]["A"]
