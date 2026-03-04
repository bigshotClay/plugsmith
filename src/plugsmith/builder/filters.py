"""Repeater filtering, distance calculation, and state tier classification."""

import logging
import math
from collections import Counter, defaultdict
from typing import Optional

from .models import Repeater
from .api import US_STATES

log = logging.getLogger(__name__)

try:
    from geopy.distance import geodesic as _geodesic
    _HAS_GEOPY = True
except ImportError:  # pragma: no cover
    _HAS_GEOPY = False  # pragma: no cover


def _state_name_to_abbr(name: str) -> str:
    """Convert full state name to two-letter abbreviation."""
    for abbr, (_, full_name) in US_STATES.items():
        if full_name.lower() == name.lower():
            return abbr
    return "??"


def _parse_tone(tone_str: str) -> Optional[float]:
    """Parse a CTCSS tone string; returns None if empty/invalid."""
    if not tone_str or tone_str in ("", "0", "0.0", "CSQ", "None"):
        return None
    try:
        val = float(tone_str)
        return val if val > 0 else None
    except ValueError:
        return None


def _haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 3959.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.asin(math.sqrt(a))


def parse_repeaters(raw_data: list[dict]) -> list[Repeater]:
    """Parse raw RepeaterBook JSON dicts into Repeater objects with source-level dedup."""
    repeaters: list[Repeater] = []
    for r in raw_data:
        try:
            freq = float(r.get("Frequency", 0))
            input_freq = float(r.get("Input Freq", 0))
            if freq == 0 or input_freq == 0:
                continue

            pl = _parse_tone(r.get("PL", ""))
            tsq = _parse_tone(r.get("TSQ", ""))
            lat = float(r.get("Lat", 0))
            lon = float(r.get("Long", 0))

            is_fm = r.get("FM Analog", "No") == "Yes"
            is_dmr = r.get("DMR", "No") == "Yes"
            is_fusion = r.get("System Fusion", "No") == "Yes"
            is_nxdn = r.get("NXDN", "No") == "Yes"
            is_p25 = r.get("APCO P-25", "No") == "Yes"
            is_m17 = r.get("M17", "No") == "Yes"
            is_tetra = r.get("Tetra", "No") == "Yes"

            cc_str = r.get("DMR Color Code", "")
            dmr_cc = int(cc_str) if cc_str and str(cc_str).isdigit() else None
            dmr_id = r.get("DMR ID", "") or None

            state_name = r.get("State", "")
            state_abbr = _state_name_to_abbr(state_name)

            def _s(val: object, default: str = "") -> str:
                v = val or default
                return v.strip() if isinstance(v, str) else default

            rpt = Repeater(
                callsign=_s(r.get("Callsign"), "UNKNOWN"),
                frequency=freq,
                input_freq=input_freq,
                offset=round(input_freq - freq, 4),
                pl_tone=pl,
                tsq_tone=tsq,
                city=_s(r.get("Nearest City")),
                county=_s(r.get("County")),
                state=state_name,
                state_abbr=state_abbr,
                lat=lat,
                lon=lon,
                use=_s(r.get("Use"), "OPEN"),
                status=_s(r.get("Operational Status")),
                is_fm=is_fm,
                is_dmr=is_dmr,
                is_fusion=is_fusion,
                is_nxdn=is_nxdn,
                is_p25=is_p25,
                dmr_color_code=dmr_cc,
                dmr_id=dmr_id,
                is_m17=is_m17,
                is_tetra=is_tetra,
                m17_can=_s(r.get("M17 CAN")) or None,
                p25_nac=_s(r.get("P-25 NAC")) or None,
                tetra_mcc=_s(r.get("Tetra MCC")) or None,
                tetra_mnc=_s(r.get("Tetra MNC")) or None,
                landmark=_s(r.get("Landmark")),
            )
            repeaters.append(rpt)
        except (ValueError, TypeError) as e:
            log.debug(f"Skipping malformed repeater entry: {e}")
            continue

    # Source-level dedup: same physical repeater can appear in multiple states' feeds
    seen: set[tuple] = set()
    unique: list[Repeater] = []
    for r in repeaters:
        key = (r.callsign.upper(), round(r.frequency, 4))
        if key not in seen:
            seen.add(key)
            unique.append(r)
    dupes = len(repeaters) - len(unique)
    if dupes:
        log.info(f"Removed {dupes} duplicate repeater entries")
    return unique


def filter_repeaters(
    repeaters: list[Repeater],
    include_fm: bool = True,
    include_dmr: bool = True,
    include_fusion: bool = False,
    include_nxdn: bool = False,
    include_p25: bool = False,
    include_m17: bool = False,
    include_tetra: bool = False,
    open_only: bool = True,
    on_air_only: bool = True,
    bands: Optional[list[str]] = None,
) -> list[Repeater]:
    """Filter repeaters by mode, status, and band."""
    if bands is None:
        bands = ["2m", "70cm"]

    filtered: list[Repeater] = []
    for r in repeaters:
        if on_air_only and r.status and "on-air" not in r.status.lower():
            continue
        if open_only and r.use and r.use.upper() not in ("OPEN", ""):
            continue

        has_wanted = (
            (include_fm and r.is_fm)
            or (include_dmr and r.is_dmr)
            or (include_fusion and r.is_fusion)
            or (include_nxdn and r.is_nxdn)
            or (include_p25 and r.is_p25)
            or (include_m17 and r.is_m17)
            or (include_tetra and r.is_tetra)
        )
        if not has_wanted:
            continue

        in_band = any(
            (band == "2m" and 144.0 <= r.frequency <= 148.0)
            or (band == "70cm" and 420.0 <= r.frequency <= 450.0)
            for band in bands
        )
        if not in_band:
            continue

        if r.lat == 0 and r.lon == 0:
            continue

        filtered.append(r)

    log.info(f"Filtered to {len(filtered)} repeaters")
    return filtered


def calculate_distances(
    repeaters: list[Repeater],
    ref_lat: float,
    ref_lon: float,
) -> None:
    """Set .distance (miles) on each repeater in-place."""
    for r in repeaters:
        if _HAS_GEOPY:
            r.distance = _geodesic((ref_lat, ref_lon), (r.lat, r.lon)).miles
        else:
            r.distance = _haversine_miles(ref_lat, ref_lon, r.lat, r.lon)


def classify_states(
    repeaters: list[Repeater],
    ref_lat: float,
    ref_lon: float,
    home_r: float = 300,
    adj_r: float = 600,
) -> dict[str, str]:
    """Classify each state into home/adjacent/shallow tier by centroid distance."""
    state_coords: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for r in repeaters:
        if r.state_abbr != "??" and (r.lat != 0 or r.lon != 0):
            state_coords[r.state_abbr].append((r.lat, r.lon))

    state_tiers: dict[str, str] = {}
    for state, coords in state_coords.items():
        cent_lat = sum(c[0] for c in coords) / len(coords)
        cent_lon = sum(c[1] for c in coords) / len(coords)
        dist = _haversine_miles(ref_lat, ref_lon, cent_lat, cent_lon)
        if dist <= home_r:
            state_tiers[state] = "home"
        elif dist <= adj_r:
            state_tiers[state] = "adjacent"
        else:
            state_tiers[state] = "shallow"

    for tier in ("home", "adjacent", "shallow"):
        tier_states = sorted(s for s, t in state_tiers.items() if t == tier)
        log.info(f"{tier.capitalize()} tier ({len(tier_states)} states): {', '.join(tier_states)}")

    return state_tiers


def compute_state_ctcss_map(repeaters: list[Repeater]) -> dict[tuple, Optional[float]]:
    """Return modal CTCSS tone per (state_abbr, round(freq, 4))."""
    tone_groups: dict[tuple, list[float]] = defaultdict(list)
    for r in repeaters:
        if r.is_fm and r.pl_tone and r.state_abbr != "??":
            key = (r.state_abbr, round(r.frequency, 4))
            tone_groups[key].append(r.pl_tone)
    return {
        k: Counter(v).most_common(1)[0][0] if v else None
        for k, v in tone_groups.items()
    }


def compute_state_input_freq_map(repeaters: list[Repeater]) -> dict[tuple, Optional[float]]:
    """Return modal TX frequency per (state_abbr, round(freq, 4))."""
    freq_groups: dict[tuple, list[float]] = defaultdict(list)
    for r in repeaters:
        if r.state_abbr != "??":
            key = (r.state_abbr, round(r.frequency, 4))
            freq_groups[key].append(r.input_freq)
    return {
        k: Counter(v).most_common(1)[0][0] if v else None
        for k, v in freq_groups.items()
    }
