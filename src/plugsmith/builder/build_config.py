"""Configuration loading and defaults for the codeplug builder."""

import os

import yaml


DEFAULT_CONFIG: dict = {
    "dmr_id": 0,
    "callsign": "N0CALL",
    "api_email": "",        # REQUIRED: your email for RepeaterBook API User-Agent
    "reference_location": {
        "lat": 38.2085,   # Sullivan, MO
        "lon": -91.1604,
    },
    "home_state": "MO",
    "states": ["MO", "IL", "AR", "KS", "OK", "TN", "KY", "IN", "IA", "NE"],
    "modes": {
        "fm": True,
        "dmr": True,
        "dstar": False,
        "fusion": False,
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
        "dmr_talkgroups_per_repeater": 7,
    },
    "adjacent_region": {
        "max_fm_per_state": 30,
        "max_dmr_freqs_per_state": 5,
        "dmr_tgs_per_freq": 3,
    },
    "shallow_region": {
        "max_fm_freqs": 10,
        "max_dmr_freqs": 3,
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
