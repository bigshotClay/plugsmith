"""RepeaterBook API client with caching."""

import json
import logging
import time
from pathlib import Path
from typing import Callable, Optional

import requests

log = logging.getLogger(__name__)

REPEATERBOOK_EXPORT = "https://www.repeaterbook.com/api/export.php"

# US State FIPS codes for RepeaterBook
US_STATES: dict[str, tuple[str, str]] = {
    "AL": ("01", "Alabama"), "AK": ("02", "Alaska"), "AZ": ("04", "Arizona"),
    "AR": ("05", "Arkansas"), "CA": ("06", "California"), "CO": ("08", "Colorado"),
    "CT": ("09", "Connecticut"), "DE": ("10", "Delaware"), "FL": ("12", "Florida"),
    "GA": ("13", "Georgia"), "HI": ("15", "Hawaii"), "ID": ("16", "Idaho"),
    "IL": ("17", "Illinois"), "IN": ("18", "Indiana"), "IA": ("19", "Iowa"),
    "KS": ("20", "Kansas"), "KY": ("21", "Kentucky"), "LA": ("22", "Louisiana"),
    "ME": ("23", "Maine"), "MD": ("24", "Maryland"), "MA": ("25", "Massachusetts"),
    "MI": ("26", "Michigan"), "MN": ("27", "Minnesota"), "MS": ("28", "Mississippi"),
    "MO": ("29", "Missouri"), "MT": ("30", "Montana"), "NE": ("31", "Nebraska"),
    "NV": ("32", "Nevada"), "NH": ("33", "New Hampshire"), "NJ": ("34", "New Jersey"),
    "NM": ("35", "New Mexico"), "NY": ("36", "New York"), "NC": ("37", "North Carolina"),
    "ND": ("38", "North Dakota"), "OH": ("39", "Ohio"), "OK": ("40", "Oklahoma"),
    "OR": ("41", "Oregon"), "PA": ("42", "Pennsylvania"), "RI": ("44", "Rhode Island"),
    "SC": ("45", "South Carolina"), "SD": ("46", "South Dakota"), "TN": ("47", "Tennessee"),
    "TX": ("48", "Texas"), "UT": ("49", "Utah"), "VT": ("50", "Vermont"),
    "VA": ("51", "Virginia"), "WA": ("53", "Washington"), "WV": ("54", "West Virginia"),
    "WI": ("55", "Wisconsin"), "WY": ("56", "Wyoming"), "DC": ("11", "District of Columbia"),
}


class RepeaterBookClient:
    """Fetches repeater data from the RepeaterBook API with file-based caching."""

    def __init__(
        self,
        cache_dir: str = ".rb_cache",
        rate_limit: float = 2.0,
        user_agent: str = "",
        progress_callback: Optional[Callable[[str, bool], None]] = None,
    ) -> None:
        """
        Args:
            cache_dir: Directory for JSON cache files.
            rate_limit: Seconds to sleep between API requests.
            user_agent: HTTP User-Agent string. Must contain a valid contact email per
                RepeaterBook ToS — generic strings get 401. Set api_email in config.yaml
                and BuildPane will construct this automatically.
            progress_callback: Called with (message, is_cached) per state fetch.
        """
        if not user_agent:
            raise ValueError(
                "RepeaterBook requires a valid email in the User-Agent. "
                "Set api_email in your config.yaml."
            )
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.rate_limit = rate_limit
        self.progress_callback = progress_callback
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})

    def _cache_path(self, state_id: str) -> Path:
        return self.cache_dir / f"state_{state_id}.json"

    def _is_cache_fresh(self, path: Path, max_age_hours: float = 12.0) -> bool:
        if not path.exists():
            return False
        age = time.time() - path.stat().st_mtime
        return age < (max_age_hours * 3600)

    def _notify(self, msg: str, is_cached: bool = False) -> None:
        if self.progress_callback:
            self.progress_callback(msg, is_cached)
        else:
            log.info(msg)

    def fetch_state(self, state_abbr: str, country: str = "United States") -> list[dict]:
        """Fetch all repeaters for a US state, using cache when fresh."""
        state_abbr = state_abbr.upper().strip()
        if state_abbr not in US_STATES:
            log.warning(f"Unknown state abbreviation: {state_abbr}")
            return []

        state_id, state_name = US_STATES[state_abbr]
        cache_path = self._cache_path(state_id)

        if self._is_cache_fresh(cache_path):
            self._notify(f"Fetching {state_name}... (cached)", is_cached=True)
            with open(cache_path) as f:
                return json.load(f)

        self._notify(f"Fetching {state_name} from RepeaterBook...", is_cached=False)
        try:
            resp = self.session.get(
                REPEATERBOOK_EXPORT,
                params={"state": state_name, "country": country},
                timeout=30,
            )
            if resp.status_code == 429:
                self._notify(f"Fetching {state_name}... (429 rate limit — waiting 90s)")
                time.sleep(90)
                resp = self.session.get(
                    REPEATERBOOK_EXPORT,
                    params={"state": state_name, "country": country},
                    timeout=30,
                )
            resp.raise_for_status()
            results = resp.json().get("results", [])

            with open(cache_path, "w") as f:
                json.dump(results, f)

            self._notify(f"Fetched {state_name}: {len(results)} repeaters")
            time.sleep(self.rate_limit)
            return results

        except requests.RequestException as e:
            log.error(f"Failed to fetch {state_name}: {e}")
            if cache_path.exists():
                self._notify(f"Fetching {state_name}... (stale cache — API error)")
                with open(cache_path) as f:
                    return json.load(f)
            return []

    def fetch_states(self, state_abbrs: list[str]) -> list[dict]:
        """Fetch repeaters for multiple states."""
        all_results: list[dict] = []
        for abbr in state_abbrs:
            results = self.fetch_state(abbr)
            all_results.extend(results)
        return all_results

    def clear_cache(self, state_abbr: str | None = None) -> int:
        """Clear cache files. Returns count of deleted files."""
        if state_abbr:
            state_abbr = state_abbr.upper().strip()
            if state_abbr in US_STATES:
                state_id = US_STATES[state_abbr][0]
                path = self._cache_path(state_id)
                if path.exists():
                    path.unlink()
                    return 1
            return 0
        count = 0
        for path in self.cache_dir.glob("state_*.json"):
            path.unlink()
            count += 1
        return count
