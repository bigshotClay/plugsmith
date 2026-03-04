"""Configuration loading and defaults for the codeplug builder."""

import os

import yaml


LOWER_48_STATES: list[str] = [
    "AL", "AR", "AZ", "CA", "CO", "CT", "DE", "FL", "GA", "IA", "ID", "IL", "IN",
    "KS", "KY", "LA", "MA", "MD", "ME", "MI", "MN", "MO", "MS", "MT", "NC", "ND",
    "NE", "NH", "NJ", "NM", "NV", "NY", "OH", "OK", "OR", "PA", "RI", "SC", "SD",
    "TN", "TX", "UT", "VA", "VT", "WA", "WI", "WV", "WY",
]


DEFAULT_CONFIG: dict = {
    "dmr_id": 0,
    "callsign": "N0CALL",
    "api_email": "",        # REQUIRED: your email for RepeaterBook API User-Agent
    "reference_location": {
        "lat": 38.2085,   # Sullivan, MO
        "lon": -91.1604,
    },
    "home_state": "MO",
    "states": LOWER_48_STATES,
    "modes": {
        "fm": True,
        "dmr": True,
        "fusion": False,
        "nxdn": False,
        "p25": False,
        "m17": False,
        "tetra": False,
    },
    "bands": ["2m", "70cm"],
    "filters": {
        "open_only": True,
        "on_air_only": True,
    },
    "organization": {
        "strategy": "tiered_region",
    },
    "tiers": {
        "home_radius_miles": 300,
        "adjacent_radius_miles": 600,
    },
    "home_region": {
        "max_fm_per_state": 150,
        "max_dmr_per_state": 100,
        "dmr_talkgroups_per_repeater": 7,
        "max_fusion_per_state": 50,
    },
    "adjacent_region": {
        "max_fm_per_state": 30,
        "max_dmr_freqs_per_state": 5,
        "dmr_tgs_per_freq": 3,
        "max_fusion_per_state": 10,
    },
    "shallow_region": {
        "max_fm_freqs": 10,
        "max_dmr_freqs": 3,
        "max_fusion_freqs": 3,
    },
    "simplex": {
        "channels": [
            {"name": "2m Simplex", "freq": 146.520},
            {"name": "70cm Simp",  "freq": 446.000},
            {"name": "2m TAC1",    "freq": 146.460},
            {"name": "2m TAC2",    "freq": 146.490},
        ]
    },
    "state_talkgroups": {},
    "talkgroups": {
        # Networks to fetch talkgroup registry from (names, descriptions).
        # "brandmeister" — BrandMeister API v2 (no auth, excellent USA coverage)
        # "tgif"         — TGIF Network API (no auth, ~2,925 talkgroups)
        "networks": ["brandmeister", "tgif"],
        # Fill the radio's DMR contact list (up to radio max, e.g. 10,000 for AT-D878UVII)
        # with named TGs from the registry. In-use TGs always come first.
        "fill_contacts": True,
        # Use RadioID per-repeater static TG assignments for home-tier DMR channels
        # instead of hardcoded BrandMeister defaults. Falls back to defaults when
        # RadioID has no data for a repeater.
        "per_repeater_lookup": True,
    },
    "roaming_zones": [],  # list of route/radius zone definitions; see docs/roaming-zones.md
    "output": {
        "qdmr_yaml": "codeplug.yaml",
        "anytone_csv_dir": "anytone_csv",
        "summary": "codeplug_summary.txt",
    },
    "cache_dir": ".rb_cache",
    "rate_limit_seconds": 2.0,
}


def load_config(config_path: str) -> dict:
    """Load configuration from YAML file, merging with defaults."""
    config = _deep_copy(DEFAULT_CONFIG)
    if config_path and os.path.exists(config_path):
        with open(config_path) as f:
            user_config = yaml.safe_load(f)
        if user_config:
            _deep_merge(config, user_config)
    return config


def _deep_copy(obj: dict) -> dict:
    """Simple deep copy for nested dicts/lists."""
    import copy
    return copy.deepcopy(obj)


def _deep_merge(base: dict, override: dict) -> None:
    """Recursively merge override into base in-place."""
    for k, v in override.items():
        if k in base and isinstance(base[k], dict) and isinstance(v, dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v


def validate_modes(config: dict, radio_profile: object) -> None:
    """Raise ValueError if any enabled mode is not supported by the radio profile.

    Args:
        config: Builder config dict (must have a "modes" key).
        radio_profile: RadioProfile instance with a supported_modes frozenset.
    """
    modes = config.get("modes", {})
    supported = getattr(radio_profile, "supported_modes", frozenset())
    unsupported = [mode for mode, enabled in modes.items() if enabled and mode not in supported]
    if unsupported:
        raise ValueError(
            f"Radio '{radio_profile.key}' does not support mode(s): {', '.join(sorted(unsupported))}. "
            f"Supported: {', '.join(sorted(supported))}"
        )


def write_default_config(path: str) -> None:
    """Write a starter config.yaml."""
    with open(path, "w") as f:
        f.write("# Codeplug Builder Configuration\n")
        f.write("# Edit this file, then build in plugsmith\n\n")
        # Only write the user-facing keys, not anytone_settings
        user_keys = {
            k: v for k, v in DEFAULT_CONFIG.items()
            if k != "anytone_settings"
        }
        yaml.dump(user_keys, f, default_flow_style=False, sort_keys=False)
