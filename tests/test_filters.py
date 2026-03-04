"""Tests for plugsmith.builder.filters."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from plugsmith.builder.filters import (
    _parse_tone,
    _state_name_to_abbr,
    _haversine_miles,
    parse_repeaters,
    filter_repeaters,
    calculate_distances,
    classify_states,
    compute_state_ctcss_map,
    compute_state_input_freq_map,
)
from plugsmith.builder.models import Repeater


# ---------------------------------------------------------------------------
# Helper: build a minimal raw repeater dict (as from RepeaterBook JSON)
# ---------------------------------------------------------------------------


def _raw(
    callsign: str = "W0TST",
    freq: float = 146.520,
    input_freq: float = 147.120,
    state: str = "Missouri",
    lat: float = 38.5,
    lon: float = -92.0,
    fm: str = "Yes",
    dmr: str = "No",
    fusion: str = "No",
    use: str = "OPEN",
    status: str = "On-air",
    pl: str = "100.0",
) -> dict:
    return {
        "Callsign": callsign,
        "Frequency": str(freq),
        "Input Freq": str(input_freq),
        "State": state,
        "Lat": str(lat),
        "Long": str(lon),
        "FM Analog": fm,
        "DMR": dmr,
        "System Fusion": fusion,
        "NXDN": "No",
        "APCO P-25": "No",
        "M17": "No",
        "Tetra": "No",
        "DMR Color Code": "",
        "DMR ID": "",
        "PL": pl,
        "TSQ": "",
        "Use": use,
        "Operational Status": status,
        "Nearest City": "TestCity",
        "County": "TestCounty",
        "Landmark": "",
    }


def _make_repeater(
    callsign: str = "W0TST",
    frequency: float = 146.520,
    input_freq: float = 147.120,
    state_abbr: str = "MO",
    lat: float = 38.5,
    lon: float = -92.0,
    is_fm: bool = True,
    is_dmr: bool = False,
    is_nxdn: bool = False,
    is_p25: bool = False,
    is_m17: bool = False,
    is_tetra: bool = False,
    pl_tone: float | None = 100.0,
    use: str = "OPEN",
    status: str = "On-air",
    distance: float = 0.0,
) -> Repeater:
    return Repeater(
        callsign=callsign,
        frequency=frequency,
        input_freq=input_freq,
        offset=round(input_freq - frequency, 4),
        pl_tone=pl_tone,
        tsq_tone=None,
        city="TestCity",
        county="TestCounty",
        state="Missouri",
        state_abbr=state_abbr,
        lat=lat,
        lon=lon,
        use=use,
        status=status,
        is_fm=is_fm,
        is_dmr=is_dmr,
        is_fusion=False,
        is_nxdn=is_nxdn,
        is_p25=is_p25,
        dmr_color_code=None,
        dmr_id=None,
        is_m17=is_m17,
        is_tetra=is_tetra,
        distance=distance,
    )


# ---------------------------------------------------------------------------
# _parse_tone
# ---------------------------------------------------------------------------


class TestParseTone:
    def test_empty_string_returns_none(self):
        assert _parse_tone("") is None

    def test_zero_string_returns_none(self):
        assert _parse_tone("0") is None

    def test_csq_returns_none(self):
        assert _parse_tone("CSQ") is None

    def test_valid_tone_returns_float(self):
        assert _parse_tone("100.0") == 100.0

    def test_valid_integer_tone(self):
        assert _parse_tone("88") == 88.0

    def test_negative_tone_returns_none(self):
        # float("-5.0") → -5.0 → val <= 0 → None
        assert _parse_tone("-5.0") is None

    def test_non_numeric_returns_none(self):
        assert _parse_tone("88.5Hz") is None

    def test_none_returns_none(self):
        assert _parse_tone(None) is None


# ---------------------------------------------------------------------------
# _state_name_to_abbr
# ---------------------------------------------------------------------------


class TestStateNameToAbbr:
    def test_known_state_returns_abbr(self):
        assert _state_name_to_abbr("Missouri") == "MO"

    def test_case_insensitive(self):
        assert _state_name_to_abbr("MISSOURI") == "MO"
        assert _state_name_to_abbr("missouri") == "MO"

    def test_unknown_state_returns_question_marks(self):
        assert _state_name_to_abbr("Narnia") == "??"


# ---------------------------------------------------------------------------
# _haversine_miles
# ---------------------------------------------------------------------------


class TestHaversineMiles:
    def test_same_point_is_zero(self):
        assert _haversine_miles(38.5, -92.0, 38.5, -92.0) == pytest.approx(0.0, abs=0.01)

    def test_known_distance(self):
        # Sullivan MO to Kansas City MO is roughly 190-200 miles
        dist = _haversine_miles(38.2085, -91.1604, 39.0997, -94.5786)
        assert 180 < dist < 210

    def test_symmetry(self):
        a = _haversine_miles(38.0, -92.0, 40.0, -90.0)
        b = _haversine_miles(40.0, -90.0, 38.0, -92.0)
        assert a == pytest.approx(b, rel=1e-6)


# ---------------------------------------------------------------------------
# parse_repeaters
# ---------------------------------------------------------------------------


class TestParseRepeaters:
    def test_parses_basic_fm_repeater(self):
        raw = [_raw()]
        result = parse_repeaters(raw)
        assert len(result) == 1
        r = result[0]
        assert r.callsign == "W0TST"
        assert r.frequency == pytest.approx(146.520)
        assert r.is_fm is True

    def test_skips_zero_frequency(self):
        raw = [_raw(freq=0.0)]
        result = parse_repeaters(raw)
        assert result == []

    def test_skips_zero_input_freq(self):
        raw = [_raw(input_freq=0.0)]
        result = parse_repeaters(raw)
        assert result == []

    def test_skips_malformed_entry(self):
        """An entry with non-numeric frequency should be skipped gracefully."""
        bad = {"Callsign": "W0BAD", "Frequency": "not-a-number", "Input Freq": "147.0",
               "State": "Missouri", "Lat": "38.5", "Long": "-92.0",
               "FM Analog": "Yes", "DMR": "No", "System Fusion": "No",
               "NXDN": "No", "APCO P-25": "No", "M17": "No", "Tetra": "No",
               "Use": "OPEN", "Operational Status": "On-air", "PL": "", "TSQ": ""}
        result = parse_repeaters([bad])
        assert result == []

    def test_deduplicates_by_callsign_and_frequency(self):
        raw = [_raw("W0DUP", 146.520), _raw("W0DUP", 146.520), _raw("W0UNQ", 147.000)]
        result = parse_repeaters(raw)
        callsigns = [r.callsign for r in result]
        assert callsigns.count("W0DUP") == 1
        assert callsigns.count("W0UNQ") == 1
        assert len(result) == 2

    def test_unknown_state_gets_question_mark_abbr(self):
        raw = [_raw(state="Narnia")]
        result = parse_repeaters(raw)
        assert result[0].state_abbr == "??"

    def test_parses_pl_tone(self):
        raw = [_raw(pl="100.0")]
        result = parse_repeaters(raw)
        assert result[0].pl_tone == pytest.approx(100.0)

    def test_parses_dmr_fields(self):
        raw = [_raw(dmr="Yes")]
        raw[0]["DMR Color Code"] = "3"
        result = parse_repeaters(raw)
        assert result[0].is_dmr is True
        assert result[0].dmr_color_code == 3

    def test_parses_all_mode_flags(self):
        row = _raw()
        row["System Fusion"] = "Yes"
        row["NXDN"] = "Yes"
        row["APCO P-25"] = "Yes"
        row["M17"] = "Yes"
        row["Tetra"] = "Yes"
        result = parse_repeaters([row])
        r = result[0]
        assert r.is_fusion is True
        assert r.is_nxdn is True
        assert r.is_p25 is True
        assert r.is_m17 is True
        assert r.is_tetra is True


# ---------------------------------------------------------------------------
# filter_repeaters
# ---------------------------------------------------------------------------


class TestFilterRepeaters:
    def test_passes_basic_open_on_air_fm(self):
        r = _make_repeater()
        result = filter_repeaters([r])
        assert len(result) == 1

    def test_excludes_off_air_when_on_air_only(self):
        r = _make_repeater(status="Off-air")
        result = filter_repeaters([r], on_air_only=True)
        assert result == []

    def test_includes_off_air_when_flag_off(self):
        r = _make_repeater(status="Off-air")
        result = filter_repeaters([r], on_air_only=False)
        assert len(result) == 1

    def test_excludes_closed_repeater_when_open_only(self):
        r = _make_repeater(use="CLOSED")
        result = filter_repeaters([r], open_only=True)
        assert result == []

    def test_includes_closed_when_flag_off(self):
        r = _make_repeater(use="CLOSED")
        result = filter_repeaters([r], open_only=False)
        assert len(result) == 1

    def test_excludes_when_no_wanted_mode(self):
        r = _make_repeater(is_fm=False)  # no DMR either
        result = filter_repeaters([r], include_fm=True)
        # No FM, no DMR → excluded
        assert result == []

    def test_includes_nxdn_when_enabled(self):
        r = _make_repeater(is_fm=False, is_nxdn=True)
        result = filter_repeaters([r], include_fm=False, include_dmr=False, include_nxdn=True)
        assert len(result) == 1

    def test_includes_p25_when_enabled(self):
        r = _make_repeater(is_fm=False, is_p25=True)
        result = filter_repeaters([r], include_fm=False, include_dmr=False, include_p25=True)
        assert len(result) == 1

    def test_includes_m17_when_enabled(self):
        r = _make_repeater(is_fm=False, is_m17=True)
        result = filter_repeaters([r], include_fm=False, include_dmr=False, include_m17=True)
        assert len(result) == 1

    def test_includes_tetra_when_enabled(self):
        r = _make_repeater(is_fm=False, is_tetra=True)
        result = filter_repeaters([r], include_fm=False, include_dmr=False, include_tetra=True)
        assert len(result) == 1

    def test_excludes_out_of_band_frequency(self):
        r = _make_repeater(frequency=220.0)  # not 2m or 70cm
        result = filter_repeaters([r])
        assert result == []

    def test_excludes_zero_lat_lon(self):
        r = _make_repeater(lat=0.0, lon=0.0)
        result = filter_repeaters([r])
        assert result == []

    def test_custom_bands_2m_only(self):
        r_2m = _make_repeater(frequency=146.520)
        r_70cm = _make_repeater(callsign="W0B", frequency=444.100, input_freq=449.100)
        result = filter_repeaters([r_2m, r_70cm], bands=["2m"])
        assert len(result) == 1
        assert result[0].callsign == "W0TST"

    def test_70cm_band_passes(self):
        r = _make_repeater(callsign="W070", frequency=444.100, input_freq=449.100)
        result = filter_repeaters([r], bands=["70cm"])
        assert len(result) == 1


# ---------------------------------------------------------------------------
# calculate_distances
# ---------------------------------------------------------------------------


class TestCalculateDistances:
    def test_sets_distance_with_geopy(self):
        r = _make_repeater(lat=38.5, lon=-92.0)
        r.distance = 0.0
        calculate_distances([r], ref_lat=38.2085, ref_lon=-91.1604)
        assert r.distance > 0

    def test_sets_distance_without_geopy(self):
        """Test that the haversine fallback path is exercised when geopy unavailable."""
        r = _make_repeater(lat=38.5, lon=-92.0)
        r.distance = 0.0
        with patch("plugsmith.builder.filters._HAS_GEOPY", False):
            calculate_distances([r], ref_lat=38.2085, ref_lon=-91.1604)
        assert r.distance > 0

    def test_empty_list_ok(self):
        calculate_distances([], ref_lat=38.0, ref_lon=-90.0)

    def test_multiple_repeaters_all_get_distances(self):
        repeaters = [_make_repeater(lat=38.5, lon=-92.0), _make_repeater(lat=39.0, lon=-94.0)]
        calculate_distances(repeaters, ref_lat=38.2085, ref_lon=-91.1604)
        assert all(r.distance > 0 for r in repeaters)


# ---------------------------------------------------------------------------
# classify_states
# ---------------------------------------------------------------------------


class TestClassifyStates:
    def _make_mo_repeaters(self, n: int = 3) -> list[Repeater]:
        return [_make_repeater(lat=38.5 + i * 0.1, lon=-92.0) for i in range(n)]

    def _make_ca_repeaters(self, n: int = 3) -> list[Repeater]:
        return [_make_repeater(callsign=f"W{i}CA", state_abbr="CA", lat=34.0 + i * 0.1, lon=-118.0) for i in range(n)]

    def test_nearby_state_is_home(self):
        repeaters = self._make_mo_repeaters()
        tiers = classify_states(repeaters, ref_lat=38.2085, ref_lon=-91.1604, home_r=300, adj_r=600)
        assert tiers.get("MO") == "home"

    def test_far_state_is_shallow(self):
        repeaters = self._make_ca_repeaters()
        tiers = classify_states(repeaters, ref_lat=38.2085, ref_lon=-91.1604, home_r=300, adj_r=600)
        assert tiers.get("CA") == "shallow"

    def test_ignores_unknown_state_abbr(self):
        r = _make_repeater(state_abbr="??", lat=38.5, lon=-92.0)
        tiers = classify_states([r], ref_lat=38.0, ref_lon=-90.0)
        assert "??" not in tiers

    def test_ignores_zero_coords(self):
        r = _make_repeater(lat=0.0, lon=0.0)
        tiers = classify_states([r], ref_lat=38.0, ref_lon=-90.0)
        assert len(tiers) == 0

    def test_adjacent_state_is_adjacent(self):
        # Columbus OH is ~449 miles from Sullivan MO → adjacent (300 < d < 600)
        r = _make_repeater(callsign="W0OH", state_abbr="OH", lat=39.96, lon=-82.99)
        tiers = classify_states([r], ref_lat=38.2085, ref_lon=-91.1604, home_r=300, adj_r=600)
        assert tiers.get("OH") == "adjacent"

    def test_empty_returns_empty(self):
        tiers = classify_states([], ref_lat=38.0, ref_lon=-90.0)
        assert tiers == {}


# ---------------------------------------------------------------------------
# compute_state_ctcss_map
# ---------------------------------------------------------------------------


class TestComputeStateCtcssMap:
    def test_returns_modal_tone(self):
        repeaters = [
            _make_repeater(frequency=146.520, state_abbr="MO", pl_tone=100.0, is_fm=True),
            _make_repeater(frequency=146.520, state_abbr="MO", pl_tone=100.0, is_fm=True),
            _make_repeater(frequency=146.520, state_abbr="MO", pl_tone=127.3, is_fm=True),
        ]
        mapping = compute_state_ctcss_map(repeaters)
        key = ("MO", round(146.520, 4))
        assert mapping[key] == pytest.approx(100.0)

    def test_skips_non_fm_repeaters(self):
        r = _make_repeater(frequency=444.100, input_freq=449.100, state_abbr="MO", is_fm=False, is_dmr=True, pl_tone=100.0)
        mapping = compute_state_ctcss_map([r])
        assert mapping == {}

    def test_skips_unknown_state(self):
        r = _make_repeater(frequency=146.520, state_abbr="??", pl_tone=100.0, is_fm=True)
        mapping = compute_state_ctcss_map([r])
        assert mapping == {}

    def test_skips_no_pl_tone(self):
        r = _make_repeater(frequency=146.520, state_abbr="MO", pl_tone=None, is_fm=True)
        mapping = compute_state_ctcss_map([r])
        assert mapping == {}

    def test_groups_by_state_and_freq(self):
        r_mo = _make_repeater(frequency=146.520, state_abbr="MO", pl_tone=100.0, is_fm=True)
        r_ks = _make_repeater(frequency=146.520, state_abbr="KS", pl_tone=127.3, is_fm=True)
        mapping = compute_state_ctcss_map([r_mo, r_ks])
        mo_key = ("MO", round(146.520, 4))
        ks_key = ("KS", round(146.520, 4))
        assert mapping[mo_key] == pytest.approx(100.0)
        assert mapping[ks_key] == pytest.approx(127.3)


# ---------------------------------------------------------------------------
# compute_state_input_freq_map
# ---------------------------------------------------------------------------


class TestComputeStateInputFreqMap:
    def test_returns_modal_input_freq(self):
        repeaters = [
            _make_repeater(frequency=146.520, input_freq=147.120, state_abbr="MO"),
            _make_repeater(frequency=146.520, input_freq=147.120, state_abbr="MO"),
            _make_repeater(frequency=146.520, input_freq=146.520, state_abbr="MO"),
        ]
        mapping = compute_state_input_freq_map(repeaters)
        key = ("MO", round(146.520, 4))
        assert mapping[key] == pytest.approx(147.120)

    def test_skips_unknown_state(self):
        r = _make_repeater(frequency=146.520, input_freq=147.120, state_abbr="??")
        mapping = compute_state_input_freq_map([r])
        assert mapping == {}

    def test_groups_by_state_and_freq(self):
        r_mo = _make_repeater(frequency=146.520, input_freq=147.120, state_abbr="MO")
        r_ks = _make_repeater(frequency=146.520, input_freq=147.000, state_abbr="KS")
        mapping = compute_state_input_freq_map([r_mo, r_ks])
        assert mapping[("MO", round(146.520, 4))] == pytest.approx(147.120)
        assert mapping[("KS", round(146.520, 4))] == pytest.approx(147.000)

    def test_empty_returns_empty(self):
        assert compute_state_input_freq_map([]) == {}
