"""Tests for plugsmith.builder.roaming module.

All HTTP calls are mocked via unittest.mock.patch.
"""

from __future__ import annotations

import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from plugsmith.builder.models import Repeater


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

def _make_repeater(
    lat: float,
    lon: float,
    callsign: str = "W0TST",
    is_fm: bool = True,
    is_dmr: bool = False,
    dmr_color_code: int | None = None,
    frequency: float = 146.520,
    input_freq: float = 147.120,
    city: str = "TestCity",
) -> Repeater:
    return Repeater(
        callsign=callsign,
        frequency=frequency,
        input_freq=input_freq,
        offset=round(input_freq - frequency, 3),
        pl_tone=100.0,
        tsq_tone=None,
        city=city,
        county="Test County",
        state="Missouri",
        state_abbr="MO",
        lat=lat,
        lon=lon,
        use="OPEN",
        status="On-air",
        is_fm=is_fm,
        is_dmr=is_dmr,
        is_fusion=False,
        is_nxdn=False,
        is_p25=False,
        dmr_color_code=dmr_color_code,
        dmr_id=None,
        distance=0.0,
    )


def _mock_nominatim(lat: str, lon: str) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = [{"lat": lat, "lon": lon}]
    return mock_resp


def _mock_osrm(coords: list[list[float]]) -> MagicMock:
    """coords in OSRM [lon, lat] format."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "routes": [{"geometry": {"coordinates": coords}}]
    }
    return mock_resp


# ---------------------------------------------------------------------------
# geocode_location
# ---------------------------------------------------------------------------

class TestGeocodeLocation:
    def test_numeric_lat_lon_comma(self):
        from plugsmith.builder.roaming import geocode_location
        with tempfile.TemporaryDirectory() as tmpdir:
            lat, lon = geocode_location("41.85,-87.65", tmpdir, "test/1.0")
        assert lat == pytest.approx(41.85)
        assert lon == pytest.approx(-87.65)

    def test_numeric_lat_lon_space(self):
        from plugsmith.builder.roaming import geocode_location
        with tempfile.TemporaryDirectory() as tmpdir:
            lat, lon = geocode_location("38.2085 -91.1604", tmpdir, "test/1.0")
        assert lat == pytest.approx(38.2085)
        assert lon == pytest.approx(-91.1604)

    def test_numeric_no_http_call(self):
        from plugsmith.builder.roaming import geocode_location
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("plugsmith.builder.roaming.requests.get") as mock_get:
                geocode_location("41.85,-87.65", tmpdir, "test/1.0")
                mock_get.assert_not_called()

    def test_city_name_calls_nominatim(self):
        from plugsmith.builder.roaming import geocode_location
        mock_resp = _mock_nominatim("41.8500", "-87.6500")
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("plugsmith.builder.roaming.requests.get", return_value=mock_resp):
                lat, lon = geocode_location("Chicago, IL", tmpdir, "plugsmith/0.2.0 (test@example.com)")
        assert lat == pytest.approx(41.85)
        assert lon == pytest.approx(-87.65)

    def test_city_name_cached_second_call(self):
        from plugsmith.builder.roaming import geocode_location
        mock_resp = _mock_nominatim("41.8500", "-87.6500")
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("plugsmith.builder.roaming.requests.get", return_value=mock_resp) as mock_get:
                geocode_location("Chicago, IL", tmpdir, "test/1.0")
                geocode_location("Chicago, IL", tmpdir, "test/1.0")
                assert mock_get.call_count == 1

    def test_empty_results_raises_value_error(self):
        from plugsmith.builder.roaming import geocode_location
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = []
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("plugsmith.builder.roaming.requests.get", return_value=mock_resp):
                with pytest.raises(ValueError, match="no results"):
                    geocode_location("Nonexistent Place XYZ123", tmpdir, "test/1.0")

    def test_cache_persisted_to_disk(self):
        from plugsmith.builder.roaming import geocode_location
        mock_resp = _mock_nominatim("38.2085", "-91.1604")
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("plugsmith.builder.roaming.requests.get", return_value=mock_resp):
                geocode_location("Sullivan, MO", tmpdir, "test/1.0")
            cache_path = os.path.join(tmpdir, "geocode_cache.json")
            assert os.path.exists(cache_path)
            with open(cache_path) as f:
                data = json.load(f)
            assert "Sullivan, MO" in data


# ---------------------------------------------------------------------------
# fetch_route_waypoints
# ---------------------------------------------------------------------------

class TestFetchRouteWaypoints:
    def test_returns_lat_lon_tuples(self):
        from plugsmith.builder.roaming import fetch_route_waypoints
        # OSRM returns [lon, lat] — should be converted to (lat, lon)
        osrm_coords = [[-87.65, 41.85], [-90.19, 38.62]]
        mock_resp = _mock_osrm(osrm_coords)
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("plugsmith.builder.roaming.requests.get", return_value=mock_resp):
                wps = fetch_route_waypoints((41.85, -87.65), (38.62, -90.19), tmpdir, "test/1.0")
        assert wps[0] == pytest.approx((41.85, -87.65))
        assert wps[1] == pytest.approx((38.62, -90.19))

    def test_osrm_exception_returns_linear_fallback(self):
        from plugsmith.builder.roaming import fetch_route_waypoints
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("plugsmith.builder.roaming.requests.get", side_effect=Exception("timeout")):
                wps = fetch_route_waypoints((41.85, -87.65), (38.62, -90.19), tmpdir, "test/1.0")
        assert len(wps) == 20
        assert wps[0] == pytest.approx((41.85, -87.65))
        assert wps[-1] == pytest.approx((38.62, -90.19))

    def test_cached_result_no_http_second_call(self):
        from plugsmith.builder.roaming import fetch_route_waypoints
        osrm_coords = [[-87.65, 41.85], [-90.19, 38.62]]
        mock_resp = _mock_osrm(osrm_coords)
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("plugsmith.builder.roaming.requests.get", return_value=mock_resp) as mock_get:
                fetch_route_waypoints((41.85, -87.65), (38.62, -90.19), tmpdir, "test/1.0")
                fetch_route_waypoints((41.85, -87.65), (38.62, -90.19), tmpdir, "test/1.0")
                assert mock_get.call_count == 1

    def test_fallback_start_end_match(self):
        from plugsmith.builder.roaming import fetch_route_waypoints
        start = (38.20, -91.16)
        end = (41.85, -87.65)
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("plugsmith.builder.roaming.requests.get", side_effect=RuntimeError("err")):
                wps = fetch_route_waypoints(start, end, tmpdir, "test/1.0")
        assert wps[0] == pytest.approx(start)
        assert wps[-1] == pytest.approx(end)


# ---------------------------------------------------------------------------
# find_repeaters_in_radius
# ---------------------------------------------------------------------------

class TestFindRepeatersInRadius:
    def test_filters_within_radius(self):
        from plugsmith.builder.roaming import find_repeaters_in_radius
        center_lat, center_lon = 38.2085, -91.1604
        close = _make_repeater(38.30, -91.16, callsign="W0CLO")  # ~6 miles
        far = _make_repeater(40.00, -91.16, callsign="W0FAR")    # ~124 miles
        result = find_repeaters_in_radius([close, far], center_lat, center_lon, 50.0)
        assert len(result) == 1
        assert result[0].callsign == "W0CLO"

    def test_sorted_by_distance_ascending(self):
        from plugsmith.builder.roaming import find_repeaters_in_radius
        center_lat, center_lon = 38.2085, -91.1604
        r_far = _make_repeater(38.40, -91.16, callsign="W0FAR")   # farther
        r_near = _make_repeater(38.25, -91.16, callsign="W0NRR")  # closer
        result = find_repeaters_in_radius([r_far, r_near], center_lat, center_lon, 100.0)
        assert result[0].callsign == "W0NRR"
        assert result[1].callsign == "W0FAR"

    def test_sets_distance_in_place(self):
        from plugsmith.builder.roaming import find_repeaters_in_radius
        r = _make_repeater(38.30, -91.16)
        find_repeaters_in_radius([r], 38.2085, -91.1604, 50.0)
        assert r.distance > 0.0

    def test_returns_empty_when_none_in_radius(self):
        from plugsmith.builder.roaming import find_repeaters_in_radius
        r = _make_repeater(45.00, -70.00, callsign="W1FAR")
        result = find_repeaters_in_radius([r], 38.2085, -91.1604, 50.0)
        assert result == []


# ---------------------------------------------------------------------------
# find_repeaters_along_route
# ---------------------------------------------------------------------------

class TestFindRepeatersAlongRoute:
    def test_filters_by_corridor(self):
        from plugsmith.builder.roaming import find_repeaters_along_route
        waypoints = [(41.85, -87.65), (40.00, -88.00), (38.62, -90.19)]
        on_route = _make_repeater(40.00, -88.05, callsign="W0ROT")   # ~2.5 miles from waypoint
        off_route = _make_repeater(35.00, -80.00, callsign="W0OFF")  # hundreds of miles away
        result = find_repeaters_along_route([on_route, off_route], waypoints, 25.0)
        callsigns = [r.callsign for r in result]
        assert "W0ROT" in callsigns
        assert "W0OFF" not in callsigns

    def test_ordered_along_route(self):
        from plugsmith.builder.roaming import find_repeaters_along_route
        waypoints = [(41.85, -87.65), (40.00, -88.00), (38.62, -90.19)]
        r_start = _make_repeater(41.80, -87.70, callsign="W0STT")  # near waypoint[0]
        r_end = _make_repeater(38.65, -90.15, callsign="W0END")    # near waypoint[2]
        result = find_repeaters_along_route([r_end, r_start], waypoints, 50.0)
        assert result[0].callsign == "W0STT"
        assert result[1].callsign == "W0END"

    def test_returns_empty_for_empty_waypoints(self):
        from plugsmith.builder.roaming import find_repeaters_along_route
        r = _make_repeater(38.0, -91.0)
        result = find_repeaters_along_route([r], [], 25.0)
        assert result == []


# ---------------------------------------------------------------------------
# build_roaming_zone_spec
# ---------------------------------------------------------------------------

class TestBuildRoamingZoneSpec:
    def test_channel_count_capped_at_max(self):
        from plugsmith.builder.roaming import build_roaming_zone_spec
        repeaters = [_make_repeater(38.0 + i * 0.01, -91.0, callsign=f"W{i:04d}") for i in range(50)]
        spec = build_roaming_zone_spec("Test", repeaters, max_channels=10, include_fm=True, include_dmr=False)
        assert len(spec["channels"]) <= 10

    def test_channel_names_max_16_chars(self):
        from plugsmith.builder.roaming import build_roaming_zone_spec
        # Callsign + city that would exceed 16 chars if not truncated
        repeaters = [_make_repeater(38.0, -91.0, callsign="W0LONGCALLSIGN", city="LongCityName")]
        spec = build_roaming_zone_spec("Test", repeaters, max_channels=10, include_fm=True, include_dmr=False)
        for ch in spec["channels"]:
            assert len(ch["name"]) <= 16

    def test_zone_spec_has_required_keys(self):
        from plugsmith.builder.roaming import build_roaming_zone_spec
        repeaters = [_make_repeater(38.0, -91.0)]
        spec = build_roaming_zone_spec("My Zone", repeaters, max_channels=10, include_fm=True, include_dmr=False)
        assert spec["name"] == "My Zone"
        assert spec["tier"] == "roaming"
        assert spec["state"] == ""
        assert "channels" in spec

    def test_include_fm_only(self):
        from plugsmith.builder.roaming import build_roaming_zone_spec
        r = _make_repeater(38.0, -91.0, is_fm=True, is_dmr=True, dmr_color_code=1)
        spec = build_roaming_zone_spec("Test", [r], max_channels=10, include_fm=True, include_dmr=False)
        types = {ch["ch_type"] for ch in spec["channels"]}
        assert types == {"analog"}

    def test_include_dmr_only(self):
        from plugsmith.builder.roaming import build_roaming_zone_spec
        r = _make_repeater(38.0, -91.0, is_fm=True, is_dmr=True, dmr_color_code=1)
        spec = build_roaming_zone_spec("Test", [r], max_channels=10, include_fm=False, include_dmr=True)
        types = {ch["ch_type"] for ch in spec["channels"]}
        assert types == {"digital"}

    def test_empty_repeaters_returns_empty_channels(self):
        from plugsmith.builder.roaming import build_roaming_zone_spec
        spec = build_roaming_zone_spec("Empty", [], max_channels=10, include_fm=True, include_dmr=True)
        assert spec["channels"] == []


# ---------------------------------------------------------------------------
# build_roaming_zones
# ---------------------------------------------------------------------------

class TestBuildRoamingZones:
    def test_skips_failing_zone_and_continues(self):
        from plugsmith.builder.roaming import build_roaming_zones
        defs = [
            {"name": "Bad Zone", "mode": "radius", "center": "Nowhere XYZ", "radius_miles": 50},
            {"name": "Good Zone", "mode": "radius", "center": "38.20,-91.16", "radius_miles": 50},
        ]
        repeaters = [_make_repeater(38.20, -91.16)]

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = []  # geocode fails for "Nowhere XYZ"

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("plugsmith.builder.roaming.requests.get", return_value=mock_resp):
                zones = build_roaming_zones(defs, repeaters, tmpdir, 160, 1000, "test/1.0")

        # Bad zone skipped; good zone (numeric center) succeeds
        assert len(zones) == 1
        assert zones[0]["name"] == "Good Zone"

    def test_respects_channel_budget_across_zones(self):
        from plugsmith.builder.roaming import build_roaming_zones
        repeaters = [
            _make_repeater(38.0, -91.0 + i * 0.1, callsign=f"W{i:04d}")
            for i in range(5)
        ]
        defs = [
            {"name": "Zone A", "mode": "radius", "center": "38.0,-91.0", "radius_miles": 999},
            {"name": "Zone B", "mode": "radius", "center": "38.0,-91.0", "radius_miles": 999},
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            zones = build_roaming_zones(defs, repeaters, tmpdir, 160, budget := 3, "test/1.0")

        total_ch = sum(len(z["channels"]) for z in zones)
        assert total_ch <= 3

    def test_returns_empty_for_empty_defs(self):
        from plugsmith.builder.roaming import build_roaming_zones
        with tempfile.TemporaryDirectory() as tmpdir:
            zones = build_roaming_zones([], [], tmpdir, 160, 1000, "test/1.0")
        assert zones == []

    def test_post_line_called_on_success(self):
        from plugsmith.builder.roaming import build_roaming_zones
        defs = [{"name": "Z", "mode": "radius", "center": "38.0,-91.0", "radius_miles": 50}]
        repeaters = [_make_repeater(38.0, -91.0)]
        messages: list[str] = []

        with tempfile.TemporaryDirectory() as tmpdir:
            build_roaming_zones(
                defs, repeaters, tmpdir, 160, 1000, "test/1.0",
                post_line=lambda msg, is_err=False: messages.append(msg),
            )

        assert any("Z" in m for m in messages)

    def test_post_line_called_on_skip(self):
        from plugsmith.builder.roaming import build_roaming_zones
        defs = [{"name": "Bad", "mode": "radius", "center": "Nowhere XYZ", "radius_miles": 50}]
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = []
        errors: list[str] = []

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("plugsmith.builder.roaming.requests.get", return_value=mock_resp):
                build_roaming_zones(
                    defs, [], tmpdir, 160, 1000, "test/1.0",
                    post_line=lambda msg, is_err=False: errors.append(msg) if is_err else None,
                )

        assert any("Bad" in m for m in errors)

    def test_zero_budget_skips_all(self):
        from plugsmith.builder.roaming import build_roaming_zones
        defs = [{"name": "Z", "mode": "radius", "center": "38.0,-91.0", "radius_miles": 50}]
        with tempfile.TemporaryDirectory() as tmpdir:
            zones = build_roaming_zones(defs, [], tmpdir, 160, 0, "test/1.0")
        assert zones == []

    def test_route_mode_uses_fetch_waypoints(self):
        from plugsmith.builder.roaming import build_roaming_zones
        defs = [{
            "name": "Route Z",
            "mode": "route",
            "waypoints": ["41.85,-87.65", "38.62,-90.19"],
            "corridor_miles": 500,
        }]
        # One repeater along the rough midpoint
        repeaters = [_make_repeater(40.0, -88.5, callsign="W0MID")]
        osrm_coords = [[-87.65, 41.85], [-88.50, 40.00], [-90.19, 38.62]]
        mock_resp = _mock_osrm(osrm_coords)

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("plugsmith.builder.roaming.requests.get", return_value=mock_resp):
                zones = build_roaming_zones(defs, repeaters, tmpdir, 160, 1000, "test/1.0")

        assert len(zones) == 1
        assert zones[0]["name"] == "Route Z"
        assert len(zones[0]["channels"]) >= 1

    def test_budget_exhausted_post_line_called(self):
        """Line 294: post_line is called when channel budget is exhausted mid-loop."""
        from plugsmith.builder.roaming import build_roaming_zones
        repeaters = [_make_repeater(38.0, -91.0 + i * 0.1, callsign=f"W{i:04d}") for i in range(5)]
        defs = [
            {"name": "Zone A", "mode": "radius", "center": "38.0,-91.0", "radius_miles": 999},
            {"name": "Zone B", "mode": "radius", "center": "38.0,-91.0", "radius_miles": 999},
        ]
        messages: list[str] = []

        with tempfile.TemporaryDirectory() as tmpdir:
            build_roaming_zones(
                defs, repeaters, tmpdir, 160, budget := 2, "test/1.0",
                post_line=lambda msg, is_err=False: messages.append(msg),
            )

        assert any("budget" in m.lower() or "exhausted" in m.lower() for m in messages)

    def test_route_zone_insufficient_waypoints_skipped(self):
        """Line 311: Route zone with < 2 waypoints raises ValueError → skipped."""
        from plugsmith.builder.roaming import build_roaming_zones
        defs = [
            {"name": "Bad Route", "mode": "route", "waypoints": ["41.85,-87.65"]},  # only 1 wp
            {"name": "Good Zone", "mode": "radius", "center": "38.0,-91.0", "radius_miles": 50},
        ]
        repeaters = [_make_repeater(38.0, -91.0)]
        with tempfile.TemporaryDirectory() as tmpdir:
            zones = build_roaming_zones(defs, repeaters, tmpdir, 160, 1000, "test/1.0")

        assert len(zones) == 1
        assert zones[0]["name"] == "Good Zone"

    def test_route_zone_post_line_called(self):
        """Line 318: post_line is called before fetching route waypoints."""
        from plugsmith.builder.roaming import build_roaming_zones
        defs = [{
            "name": "Route Z",
            "mode": "route",
            "waypoints": ["41.85,-87.65", "38.62,-90.19"],
            "corridor_miles": 500,
        }]
        repeaters = [_make_repeater(40.0, -88.5, callsign="W0MID")]
        osrm_coords = [[-87.65, 41.85], [-88.50, 40.00], [-90.19, 38.62]]
        mock_resp = _mock_osrm(osrm_coords)
        messages: list[str] = []

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("plugsmith.builder.roaming.requests.get", return_value=mock_resp):
                build_roaming_zones(
                    defs, repeaters, tmpdir, 160, 1000, "test/1.0",
                    post_line=lambda msg, is_err=False: messages.append(msg),
                )

        assert any("Route Z" in m and "waypoints" in m.lower() for m in messages)

    def test_radius_zone_missing_center_skipped(self):
        """Line 326: Radius zone without 'center' raises ValueError → skipped."""
        from plugsmith.builder.roaming import build_roaming_zones
        defs = [
            {"name": "No Center", "mode": "radius", "radius_miles": 50},  # missing center
            {"name": "Good Zone", "mode": "radius", "center": "38.0,-91.0", "radius_miles": 50},
        ]
        repeaters = [_make_repeater(38.0, -91.0)]
        with tempfile.TemporaryDirectory() as tmpdir:
            zones = build_roaming_zones(defs, repeaters, tmpdir, 160, 1000, "test/1.0")

        assert len(zones) == 1
        assert zones[0]["name"] == "Good Zone"

    def test_unknown_mode_skipped(self):
        """Line 342: Zone with unknown mode raises ValueError → skipped."""
        from plugsmith.builder.roaming import build_roaming_zones
        defs = [
            {"name": "Bad Mode", "mode": "teleport", "center": "38.0,-91.0"},
            {"name": "Good Zone", "mode": "radius", "center": "38.0,-91.0", "radius_miles": 50},
        ]
        repeaters = [_make_repeater(38.0, -91.0)]
        with tempfile.TemporaryDirectory() as tmpdir:
            zones = build_roaming_zones(defs, repeaters, tmpdir, 160, 1000, "test/1.0")

        assert len(zones) == 1
        assert zones[0]["name"] == "Good Zone"


# ---------------------------------------------------------------------------
# _load_json_cache — corrupt file (lines 44-45)
# ---------------------------------------------------------------------------


class TestLoadJsonCacheCorrupt:
    def test_corrupt_geocode_cache_falls_through(self):
        """Lines 44-45: _load_json_cache exception on corrupt JSON returns {} silently."""
        from plugsmith.builder.roaming import geocode_location

        mock_resp = _mock_nominatim("38.20", "-91.16")
        with tempfile.TemporaryDirectory() as tmpdir:
            # Write a corrupt geocode cache file
            cache_path = os.path.join(tmpdir, "geocode_cache.json")
            with open(cache_path, "w") as f:
                f.write("NOT VALID JSON {{{{")
            # geocode_location should silently ignore corrupt cache and call nominatim
            with patch("plugsmith.builder.roaming.requests.get", return_value=mock_resp) as mock_get:
                lat, lon = geocode_location("Sullivan, MO", tmpdir, "test/1.0")
            assert mock_get.called
        assert lat == pytest.approx(38.20)

    def test_corrupt_route_cache_falls_through(self):
        """Lines 149-150: fetch_route_waypoints exception on corrupt route cache falls back."""
        import hashlib
        from plugsmith.builder.roaming import fetch_route_waypoints

        start = (41.85, -87.65)
        end = (38.62, -90.19)

        with tempfile.TemporaryDirectory() as tmpdir:
            # Compute cache key exactly as roaming.py does
            slat, slon = start
            elat, elon = end
            cache_key_str = f"{slat:.4f},{slon:.4f}-{elat:.4f},{elon:.4f}"
            hash8 = hashlib.sha256(cache_key_str.encode()).hexdigest()[:8]
            cache_path = os.path.join(tmpdir, f"route_{hash8}.json")
            with open(cache_path, "w") as f:
                f.write("NOT VALID JSON {{{{")

            osrm_coords = [[-87.65, 41.85], [-90.19, 38.62]]
            mock_resp = _mock_osrm(osrm_coords)
            with patch("plugsmith.builder.roaming.requests.get", return_value=mock_resp):
                wps = fetch_route_waypoints(start, end, tmpdir, "test/1.0")

        assert len(wps) >= 2
