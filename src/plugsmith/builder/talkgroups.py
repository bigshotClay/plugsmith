"""DMR talkgroup registry — fetches from BrandMeister and TGIF with file-based caching.

Mirrors the api.py pattern for repeater fetching:
  TalkgroupClient  — fetches BrandMeister + TGIF TG lists, builds TalkgroupRegistry
  RadioIDClient    — fetches per-repeater TG assignments by state from RadioID
  TalkgroupRegistry — merged lookup table: tg_id → TalkgroupInfo
"""

import base64
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

import requests

log = logging.getLogger(__name__)

BRANDMEISTER_TG_URL = "https://api.brandmeister.network/v2/talkgroup"
TGIF_TG_URL = "https://api.tgif.network/dmr/talkgroups/json"
RADIOID_REPEATER_URL = "https://radioid.net/api/dmr/repeater/"

# TG IDs that are always PrivateCall (not GroupCall)
PRIVATE_CALL_TGS: frozenset[int] = frozenset({9998, 4000})

# Core TGs always included when filling the contact list (in priority order)
CORE_TG_IDS: list[int] = [1, 2, 3, 8, 9, 13, 91, 93, 310, 311, 312, 3100, 9998, 4000]

# US state full name → abbreviation (for RadioID state queries which want full names)
_ABBR_TO_FULLNAME: dict[str, str] = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming", "DC": "District of Columbia",
}


@dataclass
class TalkgroupInfo:
    """Metadata for a single DMR talkgroup from an external registry."""
    tg_id: int
    name: str
    call_type: str = "GroupCall"   # "GroupCall" | "PrivateCall"
    network: str = ""              # "BrandMeister" | "TGIF"
    description: str = ""


@dataclass
class RepeaterTGData:
    """Per-repeater talkgroup assignments from RadioID."""
    callsign: str
    ts1_static: list[int] = field(default_factory=list)
    ts2_static: list[int] = field(default_factory=list)


class TalkgroupRegistry:
    """Merged lookup table of TG metadata from BrandMeister and TGIF.

    Falls back to the legacy tg_name() function for unknown TG IDs so
    existing behavior is preserved when the registry is partially populated.
    """

    def __init__(self, tgs: dict[int, TalkgroupInfo]) -> None:
        self._tgs = tgs

    def name(self, tg_id: int) -> str:
        """Return human-readable name for a TG ID."""
        if tg_id in self._tgs:
            return self._tgs[tg_id].name
        # Fallback to legacy lookup (zones.py) — avoids circular import by deferring
        from plugsmith.builder.zones import tg_name as _legacy
        return _legacy(tg_id)

    def call_type(self, tg_id: int) -> str:
        """Return DMR call type for a TG ID."""
        if tg_id in self._tgs:
            return self._tgs[tg_id].call_type
        return "PrivateCall" if tg_id in PRIVATE_CALL_TGS else "GroupCall"

    def all_tgs(self) -> list[TalkgroupInfo]:
        """Return all TalkgroupInfo objects in the registry."""
        return list(self._tgs.values())

    def __len__(self) -> int:
        return len(self._tgs)

    def __contains__(self, tg_id: object) -> bool:
        return tg_id in self._tgs


class TalkgroupClient:
    """Fetches DMR talkgroup lists from BrandMeister and TGIF with file-based caching.

    Cache TTL is 24 hours (talkgroup lists change less frequently than repeater data).
    No authentication required for either source.
    """

    CACHE_MAX_AGE_HOURS = 168.0  # 7 days

    def __init__(
        self,
        cache_dir: str = ".rb_cache",
        rate_limit: float = 2.0,
        user_agent: str = "plugsmith/1.0",
        progress_callback: Optional[Callable[[str, bool], None]] = None,
    ) -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.rate_limit = rate_limit
        self.progress_callback = progress_callback
        self._last_request_time: float = 0.0
        self.session = requests.Session()
        if user_agent:
            self.session.headers.update({"User-Agent": user_agent})

    def _throttle(self) -> None:
        elapsed = time.time() - self._last_request_time
        wait = self.rate_limit - elapsed
        if wait > 0:
            time.sleep(wait)
        self._last_request_time = time.time()

    def _is_cache_fresh(self, path: Path) -> bool:
        if not path.exists():
            return False
        return (time.time() - path.stat().st_mtime) < (self.CACHE_MAX_AGE_HOURS * 3600)

    def _notify(self, msg: str, is_cached: bool = False) -> None:
        if self.progress_callback:
            self.progress_callback(msg, is_cached)
        else:
            log.info(msg)

    def _fetch_brandmeister(self) -> list[TalkgroupInfo]:
        """Fetch BrandMeister talkgroup list. Returns parsed TalkgroupInfo list."""
        cache_path = self.cache_dir / "tg_brandmeister.json"
        if self._is_cache_fresh(cache_path):
            self._notify("Fetching BrandMeister TGs… (cached)", is_cached=True)
            with open(cache_path) as f:
                raw = json.load(f)
        else:
            self._notify("Fetching BrandMeister TG list…")
            self._throttle()
            try:
                resp = self.session.get(BRANDMEISTER_TG_URL, timeout=30)
                resp.raise_for_status()
                raw = resp.json()
                with open(cache_path, "w") as f:
                    json.dump(raw, f)
            except requests.RequestException as exc:
                log.error(f"Failed to fetch BrandMeister TGs: {exc}")
                if cache_path.exists():
                    self._notify("BrandMeister TGs… (stale cache)")
                    with open(cache_path) as f:
                        raw = json.load(f)
                else:
                    return []

        # BrandMeister may return a list or a dict keyed by TG ID
        items: list = raw if isinstance(raw, list) else list(raw.values()) if isinstance(raw, dict) else []
        tgs: list[TalkgroupInfo] = []
        for item in items:
            try:
                tg_id = int(item.get("id") or item.get("tg") or 0)
                if tg_id <= 0:
                    continue
                name = str(item.get("name") or f"TG {tg_id}").strip()[:32] or f"TG {tg_id}"
                call_type = "PrivateCall" if tg_id in PRIVATE_CALL_TGS else "GroupCall"
                tgs.append(TalkgroupInfo(tg_id=tg_id, name=name, call_type=call_type, network="BrandMeister"))
            except Exception:
                continue
        self._notify(f"BrandMeister: {len(tgs)} talkgroups")
        return tgs

    def _fetch_tgif(self) -> list[TalkgroupInfo]:
        """Fetch TGIF talkgroup list. Descriptions are base64-encoded."""
        cache_path = self.cache_dir / "tg_tgif.json"
        if self._is_cache_fresh(cache_path):
            self._notify("Fetching TGIF TGs… (cached)", is_cached=True)
            with open(cache_path) as f:
                raw = json.load(f)
        else:
            self._notify("Fetching TGIF TG list…")
            self._throttle()
            try:
                resp = self.session.get(TGIF_TG_URL, timeout=30)
                resp.raise_for_status()
                raw = resp.json()
                with open(cache_path, "w") as f:
                    json.dump(raw, f)
            except requests.RequestException as exc:
                log.error(f"Failed to fetch TGIF TGs: {exc}")
                if cache_path.exists():
                    self._notify("TGIF TGs… (stale cache)")
                    with open(cache_path) as f:
                        raw = json.load(f)
                else:
                    return []

        items: list = raw if isinstance(raw, list) else []
        tgs: list[TalkgroupInfo] = []
        for item in items:
            try:
                tg_id = int(item.get("id") or 0)
                if tg_id <= 0:
                    continue
                name = str(item.get("name") or f"TG {tg_id}").strip()[:32] or f"TG {tg_id}"
                desc_b64 = item.get("description", "")
                try:
                    desc = base64.b64decode(desc_b64 + "==").decode("utf-8", errors="replace").strip()
                except Exception:
                    desc = ""
                call_type = "PrivateCall" if tg_id in PRIVATE_CALL_TGS else "GroupCall"
                tgs.append(TalkgroupInfo(
                    tg_id=tg_id, name=name, call_type=call_type, network="TGIF", description=desc
                ))
            except Exception:
                continue
        self._notify(f"TGIF: {len(tgs)} talkgroups")
        return tgs

    def fetch_registry(self, networks: Optional[list[str]] = None) -> TalkgroupRegistry:
        """Fetch TG lists from configured networks and merge into a registry.

        BrandMeister takes priority on conflicts (larger, more authoritative network).

        Args:
            networks: Network names to fetch. Defaults to ["brandmeister", "tgif"].
        """
        if networks is None:
            networks = ["brandmeister", "tgif"]

        # Fetch TGIF first (lower priority — BrandMeister will overwrite conflicts)
        merged: dict[int, TalkgroupInfo] = {}
        if "tgif" in networks:
            for tg in self._fetch_tgif():
                merged[tg.tg_id] = tg
        if "brandmeister" in networks:
            for tg in self._fetch_brandmeister():
                merged[tg.tg_id] = tg

        # Enforce correct call_type for known private-call TGs
        for tg_id in PRIVATE_CALL_TGS:
            if tg_id in merged:
                merged[tg_id].call_type = "PrivateCall"

        log.info(f"TG registry: {len(merged)} unique talkgroups from {networks}")
        return TalkgroupRegistry(merged)

    def clear_cache(self) -> int:
        """Remove TG registry cache files. Returns count deleted."""
        count = 0
        for name in ("tg_brandmeister.json", "tg_tgif.json"):
            path = self.cache_dir / name
            if path.exists():
                path.unlink()
                count += 1
        return count


class RadioIDClient:
    """Fetches per-repeater talkgroup assignments from RadioID.net by state.

    Uses the public endpoint:
        GET https://radioid.net/api/dmr/repeater/?state={full_state_name}

    Returns static TS1 and TS2 talkgroup assignments per repeater callsign.
    Results are cached per state for 24 hours.
    """

    CACHE_MAX_AGE_HOURS = 168.0  # 7 days

    def __init__(
        self,
        cache_dir: str = ".rb_cache",
        rate_limit: float = 2.0,
        user_agent: str = "plugsmith/1.0",
        progress_callback: Optional[Callable[[str, bool], None]] = None,
    ) -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.rate_limit = rate_limit
        self.progress_callback = progress_callback
        self._last_request_time: float = 0.0
        self.session = requests.Session()
        if user_agent:
            self.session.headers.update({"User-Agent": user_agent})

    def _throttle(self) -> None:
        elapsed = time.time() - self._last_request_time
        wait = self.rate_limit - elapsed
        if wait > 0:
            time.sleep(wait)
        self._last_request_time = time.time()

    def _cache_path(self, state_abbr: str) -> Path:
        return self.cache_dir / f"radioid_{state_abbr.upper()}.json"

    def _is_cache_fresh(self, path: Path) -> bool:
        if not path.exists():
            return False
        return (time.time() - path.stat().st_mtime) < (self.CACHE_MAX_AGE_HOURS * 3600)

    def _notify(self, msg: str, is_cached: bool = False) -> None:
        if self.progress_callback:
            self.progress_callback(msg, is_cached)
        else:
            log.info(msg)

    def fetch_repeater_tgs(self, state_abbr: str) -> dict[str, RepeaterTGData]:
        """Fetch per-repeater TG assignments for a US state from RadioID.

        Args:
            state_abbr: Two-letter state abbreviation (e.g. "MO").

        Returns:
            dict mapping callsign (uppercase) → RepeaterTGData with ts1/ts2 lists.
        """
        state_abbr = state_abbr.upper().strip()
        state_name = _ABBR_TO_FULLNAME.get(state_abbr)
        if not state_name:
            log.warning(f"RadioID: unknown state abbreviation '{state_abbr}'")
            return {}

        cache_path = self._cache_path(state_abbr)
        if self._is_cache_fresh(cache_path):
            self._notify(f"RadioID {state_abbr}… (cached)", is_cached=True)
            with open(cache_path) as f:
                raw = json.load(f)
        else:
            self._notify(f"Fetching RadioID TGs for {state_name}…")
            self._throttle()
            try:
                resp = self.session.get(
                    RADIOID_REPEATER_URL,
                    params={"state": state_name},
                    timeout=30,
                )
                resp.raise_for_status()
                raw = resp.json()
                with open(cache_path, "w") as f:
                    json.dump(raw, f)
            except requests.RequestException as exc:
                log.error(f"Failed to fetch RadioID data for {state_name}: {exc}")
                if cache_path.exists():
                    self._notify(f"RadioID {state_abbr}… (stale cache)")
                    with open(cache_path) as f:
                        raw = json.load(f)
                else:
                    return {}

        result: dict[str, RepeaterTGData] = {}
        for entry in raw.get("results", []):
            callsign = str(entry.get("callsign") or "").strip().upper()
            if not callsign:
                continue
            ts1 = [int(t) for t in (entry.get("ts1_static_talkgroups") or []) if t]
            ts2 = [int(t) for t in (entry.get("ts2_static_talkgroups") or []) if t]
            result[callsign] = RepeaterTGData(callsign=callsign, ts1_static=ts1, ts2_static=ts2)

        self._notify(f"RadioID {state_abbr}: {len(result)} repeater TG records")
        return result

    def fetch_states(self, state_abbrs: list[str]) -> dict[str, RepeaterTGData]:
        """Fetch RadioID TG data for multiple states. Returns merged callsign dict."""
        all_data: dict[str, RepeaterTGData] = {}
        for abbr in state_abbrs:
            all_data.update(self.fetch_repeater_tgs(abbr))
        return all_data

    def clear_cache(self, state_abbr: Optional[str] = None) -> int:
        """Remove RadioID cache files. Returns count deleted."""
        if state_abbr:
            path = self._cache_path(state_abbr)
            if path.exists():
                path.unlink()
                return 1
            return 0
        count = 0
        for path in self.cache_dir.glob("radioid_*.json"):
            path.unlink()
            count += 1
        return count
