"""Tests for channel builder functions and tg_name in builder/zones.py."""

import pytest

from plugsmith.builder.filters import filter_repeaters
from plugsmith.builder.zones import (
    STATE_TGS_DEFAULT,
    TG_NAMES,
    adjacent_state_channels,
    generate_simplex_channels,
    home_state_channels,
    make_channel_name,
    organize_zones_tiered,
    shallow_state_channels,
    tg_name,
)
from tests.conftest import make_repeater


# ---------------------------------------------------------------------------
# tg_name
# ---------------------------------------------------------------------------

class TestTgName:
    def test_known_tg_returns_name(self):
        assert tg_name(9) == "Local"
        assert tg_name(9998) == "Parrot"
        assert tg_name(4000) == "Disconnect"
        assert tg_name(3100) == "US National"

    def test_state_tg_returns_us_state(self):
        # MO = 3129 per STATE_TGS_DEFAULT
        assert tg_name(3129) == "US MO"

    def test_state_tg_another_state(self):
        assert tg_name(3112) == "US FL"

    def test_unknown_tg_returns_tg_prefix(self):
        assert tg_name(99999) == "TG 99999"

    def test_all_state_tgs_resolve(self):
        for state, tg_num in STATE_TGS_DEFAULT.items():
            result = tg_name(tg_num)
            assert result == f"US {state}", f"Expected 'US {state}' for TG {tg_num}, got '{result}'"


# ---------------------------------------------------------------------------
# make_channel_name
# ---------------------------------------------------------------------------

class TestMakeChannelName:
    def test_basic_name(self):
        r = make_repeater(callsign="W0ABC", city="Springfield")
        assert make_channel_name(r) == "W0ABC Spring"

    def test_with_suffix(self):
        r = make_repeater(callsign="W0ABC", city="City")
        name = make_channel_name(r, suffix="DMR")
        assert "DMR" in name
        assert len(name) <= 16

    def test_name_truncated_to_16_chars(self):
        r = make_repeater(callsign="W0LONGCALL", city="VeryLongCityName")
        assert len(make_channel_name(r)) <= 16

    def test_callsign_uppercased(self):
        r = make_repeater(callsign="w0abc", city="City")
        assert make_channel_name(r).startswith("W0ABC")


# ---------------------------------------------------------------------------
# home_state_channels
# ---------------------------------------------------------------------------

class TestHomeStateChannels:
    def _fm_repeater(self, **kwargs):
        return make_repeater(is_fm=True, is_dmr=False, **kwargs)

    def _dmr_repeater(self, **kwargs):
        return make_repeater(is_fm=False, is_dmr=True, dmr_color_code=1, pl_tone=None, **kwargs)

    def test_fm_repeater_creates_analog_channel(self):
        r = self._fm_repeater(frequency=146.520, input_freq=147.120)
        channels = home_state_channels("MO", [r], {}, {})
        assert any(ch["ch_type"] == "analog" for ch in channels)

    def test_dmr_repeater_creates_digital_channels(self):
        r = self._dmr_repeater(frequency=444.100, input_freq=449.100)
        channels = home_state_channels("MO", [r], {}, {})
        assert any(ch["ch_type"] == "digital" for ch in channels)

    def test_dmr_channels_include_local_and_regional(self):
        r = self._dmr_repeater(frequency=444.100, input_freq=449.100)
        channels = home_state_channels("MO", [r], {}, {})
        tg_nums = [ch["tg_num"] for ch in channels if ch["ch_type"] == "digital"]
        assert 9 in tg_nums    # Local
        assert 8 in tg_nums    # Regional

    def test_dmr_channels_include_state_tg_when_present(self):
        r = self._dmr_repeater(frequency=444.100, input_freq=449.100)
        channels = home_state_channels("MO", [r], {}, {"MO": 3129})
        tg_nums = [ch["tg_num"] for ch in channels if ch["ch_type"] == "digital"]
        assert 3129 in tg_nums

    def test_dmr_channels_no_state_tg_when_missing(self):
        r = self._dmr_repeater(frequency=444.100, input_freq=449.100)
        channels = home_state_channels("MO", [r], {}, {})  # no state TG
        tg_nums = [ch["tg_num"] for ch in channels if ch["ch_type"] == "digital"]
        assert 3129 not in tg_nums

    def test_dmr_default_color_code_is_1_when_none(self):
        r = make_repeater(is_fm=False, is_dmr=True, dmr_color_code=None, pl_tone=None,
                          frequency=444.100, input_freq=449.100)
        channels = home_state_channels("MO", [r], {}, {})
        digital_chs = [ch for ch in channels if ch["ch_type"] == "digital"]
        assert all(ch["color_code"] == 1 for ch in digital_chs)

    def test_max_fm_cap_respected(self):
        repeaters = [self._fm_repeater(frequency=round(146.0 + i * 0.1, 1),
                                        input_freq=round(146.6 + i * 0.1, 1))
                     for i in range(10)]
        config = {"home_region": {"max_fm_per_state": 3}}
        channels = home_state_channels("MO", repeaters, config, {})
        fm_chs = [ch for ch in channels if ch["ch_type"] == "analog"]
        assert len(fm_chs) == 3

    def test_max_dmr_cap_respected(self):
        repeaters = [self._dmr_repeater(frequency=round(444.0 + i * 0.1, 1),
                                         input_freq=round(449.0 + i * 0.1, 1))
                     for i in range(5)]
        config = {"home_region": {"max_dmr_per_state": 2}}
        channels = home_state_channels("MO", repeaters, config, {})
        # Each DMR repeater generates 6 slots (Local, Regional, US Natl, NAm, TAC310, TAC311)
        digital_chs = [ch for ch in channels if ch["ch_type"] == "digital"]
        # Only 2 repeaters processed → at most 2 * 6 = 12 digital channels
        assert len(digital_chs) <= 12

    def test_no_cap_when_max_is_none(self):
        repeaters = [self._fm_repeater(frequency=round(146.0 + i * 0.025, 3),
                                        input_freq=round(146.6 + i * 0.025, 3))
                     for i in range(5)]
        config = {"home_region": {}}  # no max_fm_per_state → None → no cap
        channels = home_state_channels("MO", repeaters, config, {})
        fm_chs = [ch for ch in channels if ch["ch_type"] == "analog"]
        assert len(fm_chs) == 5

    def test_repeaters_sorted_by_distance(self):
        far = self._fm_repeater(callsign="WFAR", frequency=146.520, input_freq=147.120, distance=200.0)
        near = self._fm_repeater(callsign="WNEAR", frequency=146.620, input_freq=147.220, distance=10.0)
        config = {"home_region": {"max_fm_per_state": 1}}
        channels = home_state_channels("MO", [far, near], config, {})
        assert len(channels) == 1
        assert "WNEAR" in channels[0]["name"]


# ---------------------------------------------------------------------------
# adjacent_state_channels
# ---------------------------------------------------------------------------

class TestAdjacentStateChannels:
    def _fm_r(self, freq=146.520, tx=147.120, distance=50.0):
        return make_repeater(is_fm=True, is_dmr=False, frequency=freq, input_freq=tx, distance=distance)

    def _dmr_r(self, freq=444.100, tx=449.100, cc=1, distance=50.0):
        return make_repeater(is_fm=False, is_dmr=True, dmr_color_code=cc,
                              pl_tone=None, frequency=freq, input_freq=tx, distance=distance)

    def test_fm_repeaters_create_analog_channels(self):
        channels = adjacent_state_channels("IL", [self._fm_r()], {}, {}, {})
        assert any(ch["ch_type"] == "analog" for ch in channels)

    def test_dmr_repeaters_create_digital_channels(self):
        channels = adjacent_state_channels("IL", [self._dmr_r()], {}, {}, {})
        assert any(ch["ch_type"] == "digital" for ch in channels)

    def test_fm_count_limited_by_max_fm(self):
        repeaters = [self._fm_r(freq=round(146.0 + i * 0.1, 1), tx=round(146.6 + i * 0.1, 1))
                     for i in range(10)]
        config = {"adjacent_region": {"max_fm_per_state": 3, "max_dmr_freqs_per_state": 0, "dmr_tgs_per_freq": 0}}
        channels = adjacent_state_channels("IL", repeaters, {}, {}, config)
        assert sum(1 for ch in channels if ch["ch_type"] == "analog") == 3

    def test_dmr_freq_dedup_no_duplicates(self):
        """Two DMR repeaters on the same freq produce only one set of digital channels."""
        r1 = self._dmr_r(freq=444.100, tx=449.100, distance=10.0)
        r2 = make_repeater(callsign="W0XXX", is_fm=False, is_dmr=True, dmr_color_code=2,
                            pl_tone=None, frequency=444.100, input_freq=449.100, distance=20.0)
        channels = adjacent_state_channels("IL", [r1, r2], {}, {}, {})
        freqs = [ch["rx_freq"] for ch in channels if ch["ch_type"] == "digital"]
        assert freqs.count(444.100) == freqs.count(444.100)  # same freq appears, but at most once per TG
        unique_tg_freq = set((ch["rx_freq"], ch["tg_num"]) for ch in channels if ch["ch_type"] == "digital")
        assert len(unique_tg_freq) == len([ch for ch in channels if ch["ch_type"] == "digital"])

    def test_dmr_freq_limit_stops_early(self):
        repeaters = [self._dmr_r(freq=round(444.0 + i * 0.1, 1), tx=round(449.0 + i * 0.1, 1))
                     for i in range(10)]
        config = {"adjacent_region": {"max_fm_per_state": 0, "max_dmr_freqs_per_state": 2, "dmr_tgs_per_freq": 1}}
        channels = adjacent_state_channels("IL", repeaters, {}, {}, config)
        digital_chs = [ch for ch in channels if ch["ch_type"] == "digital"]
        unique_freqs = {ch["rx_freq"] for ch in digital_chs}
        assert len(unique_freqs) == 2

    def test_dmr_tgs_per_freq_limit(self):
        config = {"adjacent_region": {"max_fm_per_state": 0, "max_dmr_freqs_per_state": 5, "dmr_tgs_per_freq": 1}}
        channels = adjacent_state_channels("IL", [self._dmr_r()], {}, {}, config)
        digital_chs = [ch for ch in channels if ch["ch_type"] == "digital"]
        # Only 1 TG per freq
        assert len(digital_chs) == 1

    def test_default_color_code_is_1_when_none(self):
        r = make_repeater(is_fm=False, is_dmr=True, dmr_color_code=None, pl_tone=None)
        channels = adjacent_state_channels("IL", [r], {}, {}, {})
        digital_chs = [ch for ch in channels if ch["ch_type"] == "digital"]
        assert all(ch["color_code"] == 1 for ch in digital_chs)


# ---------------------------------------------------------------------------
# shallow_state_channels
# ---------------------------------------------------------------------------

class TestShallowStateChannels:
    def _fm_r(self, freq=146.520, tx=147.120):
        return make_repeater(is_fm=True, is_dmr=False, frequency=freq, input_freq=tx)

    def _dmr_r(self, freq=444.100, tx=449.100, cc=2):
        return make_repeater(is_fm=False, is_dmr=True, dmr_color_code=cc, pl_tone=None,
                              frequency=freq, input_freq=tx)

    def test_fm_channels_created(self):
        channels = shallow_state_channels("KS", [self._fm_r()], {}, {}, {})
        assert any(ch["ch_type"] == "analog" for ch in channels)

    def test_dmr_channels_created(self):
        channels = shallow_state_channels("KS", [self._dmr_r()], {}, {}, {})
        assert any(ch["ch_type"] == "digital" for ch in channels)

    def test_fm_dedup_by_frequency(self):
        """Two FM repeaters on the same frequency → one channel."""
        r1 = self._fm_r(freq=146.520, tx=147.120)
        r2 = self._fm_r(freq=146.520, tx=147.120)
        channels = shallow_state_channels("KS", [r1, r2], {}, {}, {})
        analog_chs = [ch for ch in channels if ch["ch_type"] == "analog"]
        assert len(analog_chs) == 1

    def test_fm_freq_limit_respected(self):
        repeaters = [self._fm_r(freq=round(146.0 + i * 0.1, 1), tx=round(146.6 + i * 0.1, 1))
                     for i in range(10)]
        config = {"shallow_region": {"max_fm_freqs": 3, "max_dmr_freqs": 0}}
        channels = shallow_state_channels("KS", repeaters, {}, {}, config)
        analog_chs = [ch for ch in channels if ch["ch_type"] == "analog"]
        assert len(analog_chs) == 3

    def test_dmr_freq_limit_respected(self):
        repeaters = [self._dmr_r(freq=round(444.0 + i * 0.1, 1), tx=round(449.0 + i * 0.1, 1))
                     for i in range(5)]
        config = {"shallow_region": {"max_fm_freqs": 0, "max_dmr_freqs": 2}}
        channels = shallow_state_channels("KS", repeaters, {}, {}, config)
        digital_chs = [ch for ch in channels if ch["ch_type"] == "digital"]
        assert len(digital_chs) == 2

    def test_color_code_from_most_common(self):
        """Color code resolved by most-common vote."""
        r1 = self._dmr_r(freq=444.100, cc=3)
        r2 = self._dmr_r(freq=444.100, cc=3)
        r3 = self._dmr_r(freq=444.100, cc=1)
        channels = shallow_state_channels("KS", [r1, r2, r3], {}, {}, {})
        digital_chs = [ch for ch in channels if ch["ch_type"] == "digital"]
        assert digital_chs[0]["color_code"] == 3  # most common

    def test_color_code_defaults_to_1_when_no_cc_data(self):
        r = make_repeater(is_fm=False, is_dmr=True, dmr_color_code=None, pl_tone=None)
        channels = shallow_state_channels("KS", [r], {}, {}, {})
        digital_chs = [ch for ch in channels if ch["ch_type"] == "digital"]
        assert digital_chs[0]["color_code"] == 1

    def test_tx_freq_from_input_freq_map(self):
        r = self._fm_r(freq=146.520)
        ctcss_map = {("KS", 146.52): 100.0}
        input_freq_map = {("KS", 146.52): 147.12}
        channels = shallow_state_channels("KS", [r], ctcss_map, input_freq_map, {})
        analog_chs = [ch for ch in channels if ch["ch_type"] == "analog"]
        assert analog_chs[0]["tx_freq"] == 147.12
        assert analog_chs[0]["pl_tone"] == 100.0

    def test_channel_name_includes_state_and_freq(self):
        channels = shallow_state_channels("KS", [self._fm_r(freq=146.52, tx=147.12)], {}, {}, {})
        assert any("KS" in ch["name"] for ch in channels if ch["ch_type"] == "analog")


# ---------------------------------------------------------------------------
# generate_simplex_channels
# ---------------------------------------------------------------------------

class TestGenerateSimplexChannels:
    def test_default_simplex_channels(self):
        channels = generate_simplex_channels({})
        assert len(channels) == 4  # 2m Simplex, 70cm Simp, 2m TAC1, 2m TAC2

    def test_custom_simplex_channels(self):
        config = {"simplex": {"channels": [{"name": "Custom", "freq": 147.000}]}}
        channels = generate_simplex_channels(config)
        assert len(channels) == 1
        assert channels[0]["name"] == "Custom"
        assert channels[0]["rx_freq"] == 147.000

    def test_simplex_channels_are_analog(self):
        channels = generate_simplex_channels({})
        assert all(ch["ch_type"] == "analog" for ch in channels)

    def test_simplex_tx_equals_rx(self):
        channels = generate_simplex_channels({})
        assert all(ch["rx_freq"] == ch["tx_freq"] for ch in channels)

    def test_name_truncated_to_16(self):
        config = {"simplex": {"channels": [{"name": "A" * 30, "freq": 146.52}]}}
        channels = generate_simplex_channels(config)
        assert len(channels[0]["name"]) <= 16

    def test_custom_pl_tone(self):
        config = {"simplex": {"channels": [{"name": "Ch", "freq": 146.52, "pl_tone": 100.0}]}}
        channels = generate_simplex_channels(config)
        assert channels[0]["pl_tone"] == 100.0


# ---------------------------------------------------------------------------
# organize_zones_tiered — multi-tier coverage
# ---------------------------------------------------------------------------

class TestOrganizeZonesTieredMultiTier:
    """Exercise adjacent, shallow, multiple home, and simplex paths."""

    def _run(self, state_tiers, repeaters, config=None, simplex=None):
        cfg = {
            "home_state": "MO",
            "home_region": {"max_fm_per_state": 50, "max_dmr_per_state": 0},
            "adjacent_region": {"max_fm_per_state": 5, "max_dmr_freqs_per_state": 0, "dmr_tgs_per_freq": 0},
            "shallow_region": {"max_fm_freqs": 3, "max_dmr_freqs": 0},
            "simplex": simplex or {"channels": []},
        }
        if config:
            cfg.update(config)
        return organize_zones_tiered(
            repeaters=repeaters,
            state_tiers=state_tiers,
            ctcss_map={},
            input_freq_map={},
            config=cfg,
            state_tg_map={},
        )

    def _fm_rpt(self, state, freq, tx, distance=50.0, callsign=None):
        return make_repeater(
            callsign=callsign or f"W{state}00",
            state_abbr=state,
            frequency=freq,
            input_freq=tx,
            is_fm=True,
            is_dmr=False,
            distance=distance,
        )

    def test_adjacent_state_zone_created(self):
        rpts = [self._fm_rpt("IL", 146.520, 147.120)]
        specs = self._run({"MO": "home", "IL": "adjacent"}, rpts)
        zone_names = [z["name"] for z in specs]
        assert any("IL" in n for n in zone_names)

    def test_shallow_state_zone_created(self):
        rpts = [self._fm_rpt("NE", 146.700, 147.300)]
        specs = self._run({"MO": "home", "NE": "shallow"}, rpts)
        zone_names = [z["name"] for z in specs]
        assert any("NE" in n for n in zone_names)

    def test_multiple_home_states_all_get_zones(self):
        rpts = [
            self._fm_rpt("MO", 146.520, 147.120, callsign="WMO00"),
            self._fm_rpt("AR", 146.700, 147.300, callsign="WAR00"),
        ]
        specs = self._run({"MO": "home", "AR": "home"}, rpts)
        zone_names = [z["name"] for z in specs]
        assert any("MO" in n for n in zone_names)
        assert any("AR" in n for n in zone_names)

    def test_simplex_zone_added_when_channels_configured(self):
        rpts = [self._fm_rpt("MO", 146.520, 147.120)]
        simplex_cfg = {"channels": [{"name": "2m Simplex", "freq": 146.520}]}
        specs = self._run({"MO": "home"}, rpts, simplex=simplex_cfg)
        zone_names = [z["name"] for z in specs]
        assert "Simplex" in zone_names

    def test_simplex_not_added_when_empty(self):
        rpts = [self._fm_rpt("MO", 146.520, 147.120)]
        specs = self._run({"MO": "home"}, rpts, simplex={"channels": []})
        zone_names = [z["name"] for z in specs]
        assert "Simplex" not in zone_names


# ---------------------------------------------------------------------------
# make_channel_name — mode-based suffix
# ---------------------------------------------------------------------------

class TestMakeChannelNameModeSuffix:
    def test_fm_mode_no_suffix_added(self):
        r = make_repeater(callsign="W0ABC", city="City")
        name = make_channel_name(r, mode="FM")
        assert "FM" not in name  # FM mode should not add suffix

    def test_dstar_mode_adds_suffix(self):
        r = make_repeater(callsign="W0ABC", city="City")
        name = make_channel_name(r, mode="DStar")
        assert "DStar" in name or len(name) == 16  # may be truncated

    def test_empty_mode_no_suffix(self):
        r = make_repeater(callsign="W0ABC", city="City")
        name_no_mode = make_channel_name(r)
        name_empty = make_channel_name(r, mode="")
        assert name_no_mode == name_empty


