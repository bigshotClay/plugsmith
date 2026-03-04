"""Geocoding, routing, and roaming zone generation for plugsmith."""

from __future__ import annotations

import hashlib
import json
import logging
import math
import os
from typing import Callable, Optional

import requests

from .models import Repeater
from .zones import make_channel_name

log = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return distance in miles between two lat/lon points."""
    R = 3959.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.asin(math.sqrt(a))


def _load_json_cache(path: str) -> dict:
    """Load a JSON cache file or return empty dict."""
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_json_cache(path: str, data: dict) -> None:
    """Save data to JSON cache file, creating parent dirs as needed."""
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f)


def _linear_interpolate(
    start: tuple[float, float], end: tuple[float, float], n: int = 20
) -> list[tuple[float, float]]:
    """Return n linearly interpolated (lat, lon) tuples from start to end inclusive."""
    points = []
    for i in range(n):
        t = i / (n - 1) if n > 1 else 0.0
        lat = start[0] + t * (end[0] - start[0])
        lon = start[1] + t * (end[1] - start[1])
        points.append((lat, lon))
    return points


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def geocode_location(query: str, cache_dir: str, user_agent: str) -> tuple[float, float]:
    """Return (lat, lon) for a location query.

    If query looks like 'lat,lon' or 'lat lon', parse directly (no HTTP).
    Otherwise call Nominatim. Results are cached in {cache_dir}/geocode_cache.json.

    Raises ValueError if geocoding returns no results.
    """
    query = query.strip()

    # Try numeric 'lat,lon' or 'lat lon'
    for sep in (",", " "):
        parts = query.split(sep, 1)
        if len(parts) == 2:
            try:
                lat = float(parts[0].strip())
                lon = float(parts[1].strip())
                return (lat, lon)
            except ValueError:
                pass

    # Check disk cache
    cache_path = os.path.join(cache_dir, "geocode_cache.json")
    cache = _load_json_cache(cache_path)
    if query in cache:
        entry = cache[query]
        return (entry["lat"], entry["lon"])

    # Nominatim API call
    resp = requests.get(
        NOMINATIM_URL,
        params={"q": query, "format": "json", "limit": 1},
        headers={"User-Agent": user_agent},
        timeout=10,
    )
    resp.raise_for_status()
    results = resp.json()

    if not results:
        raise ValueError(f"Geocoding returned no results for: {query!r}")

    lat = float(results[0]["lat"])
    lon = float(results[0]["lon"])

    cache[query] = {"lat": lat, "lon": lon}
    _save_json_cache(cache_path, cache)

    return (lat, lon)


def fetch_route_waypoints(
    start: tuple[float, float],
    end: tuple[float, float],
    cache_dir: str,
    user_agent: str,
) -> list[tuple[float, float]]:
    """Return route geometry as a list of (lat, lon) tuples via OSRM.

    Cached in {cache_dir}/route_{hash8}.json.
    Falls back to 20 linearly interpolated points on any failure.
    """
    slat, slon = start
    elat, elon = end

    cache_key_str = f"{slat:.4f},{slon:.4f}-{elat:.4f},{elon:.4f}"
    hash8 = hashlib.sha256(cache_key_str.encode()).hexdigest()[:8]
    cache_path = os.path.join(cache_dir, f"route_{hash8}.json")

    # Check disk cache
    if os.path.exists(cache_path):
        try:
            with open(cache_path) as f:
                cached = json.load(f)
            return [tuple(pt) for pt in cached]
        except Exception:
            pass

    # OSRM public API — note OSRM uses lon,lat order
    try:
        url = (
            f"https://router.project-osrm.org/route/v1/driving/"
            f"{slon},{slat};{elon},{elat}"
            f"?overview=full&geometries=geojson"
        )
        resp = requests.get(url, headers={"User-Agent": user_agent}, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        # GeoJSON coordinates are [lon, lat] — convert to (lat, lon) tuples
        coords = data["routes"][0]["geometry"]["coordinates"]
        waypoints = [(float(c[1]), float(c[0])) for c in coords]

        # Save to cache
        os.makedirs(cache_dir, exist_ok=True)
        with open(cache_path, "w") as f:
            json.dump(waypoints, f)

        return waypoints

    except Exception as exc:
        log.warning("OSRM routing failed (%s); falling back to linear interpolation", exc)
        return _linear_interpolate(start, end, n=20)


def find_repeaters_in_radius(
    repeaters: list[Repeater],
    center_lat: float,
    center_lon: float,
    radius_miles: float,
) -> list[Repeater]:
    """Return repeaters within radius_miles of center, sorted by distance.

    Sets repeater.distance in-place for each match.
    """
    results = []
    for r in repeaters:
        d = _haversine(center_lat, center_lon, r.lat, r.lon)
        if d <= radius_miles:
            r.distance = d
            results.append(r)
    results.sort(key=lambda r: r.distance)
    return results


def find_repeaters_along_route(
    repeaters: list[Repeater],
    waypoints: list[tuple[float, float]],
    corridor_miles: float,
) -> list[Repeater]:
    """Return repeaters within corridor_miles of the route, ordered along the route.

    For each repeater, finds the closest waypoint; sorts by that index then by
    distance, giving a natural ordered-along-route result.
    """
    tagged: list[tuple[int, float, Repeater]] = []
    for r in repeaters:
        min_dist = float("inf")
        min_idx = 0
        for i, (wlat, wlon) in enumerate(waypoints):
            d = _haversine(r.lat, r.lon, wlat, wlon)
            if d < min_dist:
                min_dist = d
                min_idx = i
        if min_dist <= corridor_miles:
            tagged.append((min_idx, min_dist, r))

    tagged.sort(key=lambda x: (x[0], x[1]))
    return [r for _, _, r in tagged]


def build_roaming_zone_spec(
    name: str,
    repeaters: list[Repeater],
    max_channels: int,
    include_fm: bool,
    include_dmr: bool,
) -> dict:
    """Return a zone spec dict compatible with organize_zones_tiered output.

    Format: {name, tier='roaming', state='', channels: [channel_dict, ...]}
    Channel names are generated via make_channel_name() and capped at 16 chars.
    """
    channels: list[dict] = []

    for r in repeaters:
        if len(channels) >= max_channels:
            break
        if r.is_fm and include_fm:
            ch_name = make_channel_name(r, mode="FM")
            channels.append({
                "ch_type": "analog",
                "name": ch_name,
                "rx_freq": r.frequency,
                "tx_freq": r.input_freq,
                "pl_tone": r.pl_tone,
                "tsq_tone": r.tsq_tone,
            })
        if r.is_dmr and include_dmr and r.dmr_color_code is not None:
            if len(channels) < max_channels:
                ch_name = make_channel_name(r, mode="DMR")
                channels.append({
                    "ch_type": "digital",
                    "name": ch_name,
                    "rx_freq": r.frequency,
                    "tx_freq": r.input_freq,
                    "color_code": r.dmr_color_code,
                    "time_slot": 1,
                    "tg_num": 9,
                    "tg_name": "Local",
                })

    return {
        "name": name,
        "tier": "roaming",
        "state": "",
        "channels": channels,
    }


def build_roaming_zones(
    roaming_defs: list[dict],
    all_repeaters: list[Repeater],
    cache_dir: str,
    max_channels_per_zone: int,
    channel_budget: int,
    user_agent: str,
    post_line: Optional[Callable[[str, bool], None]] = None,
) -> list[dict]:
    """Process all roaming zone definitions into zone spec dicts.

    Skips (logs) any definition that raises an exception.
    Respects channel_budget across all zones combined.
    """
    zone_specs: list[dict] = []
    remaining_budget = channel_budget

    for defn in roaming_defs:
        if remaining_budget <= 0:
            if post_line:
                post_line("Channel budget exhausted; skipping remaining roaming zones.", False)
            break

        name = defn.get("name", "Roaming Zone")
        mode = defn.get("mode", "radius")
        include_fm = defn.get("include_fm", True)
        include_dmr = defn.get("include_dmr", True)
        zone_max = min(
            defn.get("max_channels", max_channels_per_zone),
            max_channels_per_zone,
            remaining_budget,
        )

        try:
            if mode == "route":
                waypoints_raw = defn.get("waypoints", [])
                if len(waypoints_raw) < 2:
                    raise ValueError(f"Route zone '{name}' requires at least 2 waypoints")

                start_coords = geocode_location(waypoints_raw[0], cache_dir, user_agent)
                end_coords = geocode_location(waypoints_raw[-1], cache_dir, user_agent)
                corridor_miles = float(defn.get("corridor_miles", 25))

                if post_line:
                    post_line(f"  Roaming '{name}': fetching route waypoints…", False)

                wps = fetch_route_waypoints(start_coords, end_coords, cache_dir, user_agent)
                candidates = find_repeaters_along_route(all_repeaters, wps, corridor_miles)

            elif mode == "radius":
                center_str = defn.get("center", "")
                if not center_str:
                    raise ValueError(f"Radius zone '{name}' requires 'center'")

                center_coords = geocode_location(center_str, cache_dir, user_agent)
                radius_miles = float(defn.get("radius_miles", 50))

                if post_line:
                    post_line(
                        f"  Roaming '{name}': radius {radius_miles}mi around {center_str}…",
                        False,
                    )

                candidates = find_repeaters_in_radius(
                    all_repeaters, center_coords[0], center_coords[1], radius_miles
                )

            else:
                raise ValueError(f"Unknown roaming zone mode: {mode!r}")

            spec = build_roaming_zone_spec(name, candidates, zone_max, include_fm, include_dmr)
            zone_specs.append(spec)
            remaining_budget -= len(spec["channels"])

            if post_line:
                post_line(f"  Roaming '{name}': {len(spec['channels'])} channels", False)

        except Exception as exc:
            log.warning("Skipping roaming zone '%s': %s", name, exc)
            if post_line:
                post_line(f"  Skipping roaming zone '{name}': {exc}", True)

    return zone_specs
