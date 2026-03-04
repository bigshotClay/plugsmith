"""Zone organization strategies: tiered_region (primary) and legacy strategies."""

import logging
from collections import Counter, defaultdict
from typing import Optional

from .models import Repeater

log = logging.getLogger(__name__)

MAX_CHANNELS = 4000
MAX_ZONES = 250
MAX_CHANNELS_PER_ZONE = 160
CHANNEL_NAME_MAX = 16

# State DMR talkgroup numbers (BrandMeister)
STATE_TGS_DEFAULT: dict[str, int] = {
    "AK": 3102, "AL": 3101, "AR": 3105, "AZ": 3104, "CA": 3106,
    "CO": 3108, "CT": 3109, "DC": 3111, "DE": 3110, "FL": 3112,
    "GA": 3113, "HI": 3115, "IA": 3119, "ID": 3116, "IL": 3117,
    "IN": 3118, "KS": 3120, "KY": 3121, "LA": 3122, "MA": 3125,
    "MD": 3124, "ME": 3123, "MI": 3126, "MN": 3127, "MO": 3129,
    "MS": 3128, "MT": 3130, "NC": 3137, "ND": 3138, "NE": 3131,
    "NH": 3133, "NJ": 3134, "NM": 3135, "NV": 3132, "NY": 3136,
    "OH": 3139, "OK": 3140, "OR": 3141, "PA": 3142, "RI": 3144,
    "SC": 3145, "SD": 3146, "TN": 3147, "TX": 3148, "UT": 3149,
    "VA": 3151, "VT": 3150, "WA": 3153, "WI": 3155, "WV": 3154, "WY": 3156,
}

# Human-readable names for well-known DMR TG numbers
TG_NAMES: dict[int, str] = {
    1: "WW", 8: "Regional", 9: "Local", 13: "WW English",
    91: "WW 1", 93: "NAm", 310: "TAC 310", 311: "TAC 311",
    312: "TAC 312", 3100: "US National", 4000: "Disconnect", 9998: "Parrot",
}


def tg_name(tg_num: int) -> str:
    if tg_num in TG_NAMES:
        return TG_NAMES[tg_num]
    for state, tg in STATE_TGS_DEFAULT.items():
        if tg == tg_num:
            return f"US {state}"
    return f"TG {tg_num}"


def make_channel_name(repeater: Repeater, mode: str = "FM", suffix: str = "") -> str:
    """Generate a short, readable channel name ≤16 chars: 'CALLSIGN CITY'."""
    call = repeater.callsign.upper()
    city = repeater.city.replace(" ", "")[:6]
    name = f"{call} {city}"
    if suffix:
        name = f"{name} {suffix}"
    return name[:CHANNEL_NAME_MAX]


# ---------------------------------------------------------------------------
# Home / Adjacent / Shallow channel builders
# ---------------------------------------------------------------------------

def home_state_channels(
    state: str,
    state_repeaters: list[Repeater],
    config: dict,
    state_tg_map: dict[str, int],
) -> list[dict]:
    """Build per-repeater channels for a home-tier state."""
    home_cfg = config.get("home_region", {})
    max_fm = home_cfg.get("max_fm_per_state")
    max_dmr = home_cfg.get("max_dmr_per_state")
    state_tg = state_tg_map.get(state)

    channels: list[dict] = []
    rpts = sorted(state_repeaters, key=lambda r: r.distance)
    fm_count = 0
    dmr_count = 0

    for r in rpts:
        if r.is_fm and (max_fm is None or fm_count < max_fm):
            fm_count += 1
            channels.append({
                "ch_type": "analog",
                "name": make_channel_name(r, "FM"),
                "rx_freq": r.frequency,
                "tx_freq": r.input_freq,
                "pl_tone": r.pl_tone,
                "tsq_tone": None,
            })

        if r.is_dmr and (max_dmr is None or dmr_count < max_dmr):
            dmr_count += 1
            cc = r.dmr_color_code if r.dmr_color_code else 1
            dmr_slots = [
                (1, 9, "Local"),
                (1, 8, "Regional"),
            ]
            if state_tg:
                dmr_slots.append((1, state_tg, "State"))
            dmr_slots.extend([
                (2, 3100, "US Natl"),
                (2, 93, "NAm"),
                (2, 310, "TAC310"),
                (2, 311, "TAC311"),
            ])
            for ts, tg_num, label in dmr_slots:
                name = f"{r.callsign[:9]} {label}"[:CHANNEL_NAME_MAX]
                channels.append({
                    "ch_type": "digital",
                    "name": name,
                    "rx_freq": r.frequency,
                    "tx_freq": r.input_freq,
                    "color_code": cc,
                    "time_slot": ts,
                    "tg_num": tg_num,
                    "tg_name": label,
                })

    return channels


def adjacent_state_channels(
    state: str,
    state_repeaters: list[Repeater],
    ctcss_map: dict,
    input_freq_map: dict,
    config: dict,
) -> list[dict]:
    """Build channels for an adjacent-tier state."""
    adj_cfg = config.get("adjacent_region", {})
    max_fm = adj_cfg.get("max_fm_per_state", 30)
    max_dmr_freqs = adj_cfg.get("max_dmr_freqs_per_state", 5)
    dmr_tgs = adj_cfg.get("dmr_tgs_per_freq", 3)

    rpts = sorted(state_repeaters, key=lambda r: r.distance)
    channels: list[dict] = []

    fm_rpts = [r for r in rpts if r.is_fm][:max_fm]
    for r in fm_rpts:
        channels.append({
            "ch_type": "analog",
            "name": make_channel_name(r, "FM"),
            "rx_freq": r.frequency,
            "tx_freq": r.input_freq,
            "pl_tone": r.pl_tone,
            "tsq_tone": None,
        })

    dmr_tg_configs = [
        (1, 9,    "Local"),
        (2, 3100, "US Natl"),
        (2, 93,   "NAm"),
    ][:dmr_tgs]

    seen_dmr_freqs: list[float] = []
    for r in rpts:
        if not r.is_dmr:
            continue
        freq_key = round(r.frequency, 4)
        if freq_key in seen_dmr_freqs:
            continue
        if len(seen_dmr_freqs) >= max_dmr_freqs:
            break
        seen_dmr_freqs.append(freq_key)
        cc = r.dmr_color_code if r.dmr_color_code else 1
        for ts, tg_num, label in dmr_tg_configs:
            name = f"{r.callsign[:9]} {label}"[:CHANNEL_NAME_MAX]
            channels.append({
                "ch_type": "digital",
                "name": name,
                "rx_freq": r.frequency,
                "tx_freq": r.input_freq,
                "color_code": cc,
                "time_slot": ts,
                "tg_num": tg_num,
                "tg_name": label,
            })

    return channels


def shallow_state_channels(
    state: str,
    state_repeaters: list[Repeater],
    ctcss_map: dict,
    input_freq_map: dict,
    config: dict,
) -> list[dict]:
    """Build frequency-deduped channels for a shallow-tier state."""
    sha_cfg = config.get("shallow_region", {})
    max_fm = sha_cfg.get("max_fm_freqs", 10)
    max_dmr = sha_cfg.get("max_dmr_freqs", 3)

    fm_freq_counts: Counter = Counter()
    dmr_freq_counts: Counter = Counter()
    dmr_cc_by_freq: dict[float, list[int]] = defaultdict(list)

    for r in state_repeaters:
        if r.is_fm:
            fm_freq_counts[round(r.frequency, 4)] += 1
        if r.is_dmr:
            freq_key = round(r.frequency, 4)
            dmr_freq_counts[freq_key] += 1
            if r.dmr_color_code:
                dmr_cc_by_freq[freq_key].append(r.dmr_color_code)

    channels: list[dict] = []

    for freq, _ in fm_freq_counts.most_common(max_fm):
        key = (state, freq)
        tx_freq = input_freq_map.get(key) or freq
        pl_tone = ctcss_map.get(key)
        name = f"{state} {freq:.3f}"[:CHANNEL_NAME_MAX]
        channels.append({
            "ch_type": "analog",
            "name": name,
            "rx_freq": freq,
            "tx_freq": tx_freq,
            "pl_tone": pl_tone,
            "tsq_tone": None,
        })

    for freq, _ in dmr_freq_counts.most_common(max_dmr):
        key = (state, freq)
        tx_freq = input_freq_map.get(key) or freq
        cc_list = dmr_cc_by_freq.get(freq, [])
        cc = Counter(cc_list).most_common(1)[0][0] if cc_list else 1
        name = f"{state} {freq:.3f} D"[:CHANNEL_NAME_MAX]
        channels.append({
            "ch_type": "digital",
            "name": name,
            "rx_freq": freq,
            "tx_freq": tx_freq,
            "color_code": cc,
            "time_slot": 1,
            "tg_num": 9,
            "tg_name": "Local",
        })

    return channels


def generate_simplex_channels(config: dict) -> list[dict]:
    """Generate simplex channel entries from config."""
    default_simplex = [
        {"name": "2m Simplex", "freq": 146.520},
        {"name": "70cm Simp",  "freq": 446.000},
        {"name": "2m TAC1",    "freq": 146.460},
        {"name": "2m TAC2",    "freq": 146.490},
    ]
    channels_conf = config.get("simplex", {}).get("channels", default_simplex)
    return [
        {
            "ch_type": "analog",
            "name": ch_conf["name"][:CHANNEL_NAME_MAX],
            "rx_freq": ch_conf["freq"],
            "tx_freq": ch_conf["freq"],
            "pl_tone": ch_conf.get("pl_tone"),
            "tsq_tone": None,
        }
        for ch_conf in channels_conf
    ]


def _add_zone_with_overflow(
    zone_specs: list[dict],
    base_name: str,
    channels: list[dict],
    tier: str,
    state: str,
    max_per_zone: int = MAX_CHANNELS_PER_ZONE,
) -> None:
    """Append channels as one or more zone dicts, splitting on overflow."""
    if not channels:
        return
    for i in range(0, len(channels), max_per_zone):
        chunk = channels[i : i + max_per_zone]
        part_num = (i // max_per_zone) + 1
        if part_num == 1:
            name = base_name[:CHANNEL_NAME_MAX]
        else:
            suffix = f" {part_num}"
            name = f"{base_name[:CHANNEL_NAME_MAX - len(suffix)]}{suffix}"
        zone_specs.append({
            "name": name,
            "tier": tier,
            "state": state,
            "channels": chunk,
        })


def scale_config_to_radio(
    config: dict,
    radio_profile: "RadioProfile",
    state_tiers: dict[str, str],
) -> dict:
    """Return a shallow-copied config with channel caps scaled to the radio's capacity.

    Caps are scaled proportionally from the 4000-channel defaults.  User-set values
    that are already lower than the scaled value are always respected (never scaled up).
    """
    import copy
    from plugsmith.tool_discovery import RadioProfile  # noqa: F401 (type hint only)

    scale = radio_profile.max_channels / MAX_CHANNELS  # e.g. 0.256 for GD-77

    config = copy.deepcopy(config)

    def _apply(section: str, key: str, default: int) -> None:
        sec = config.setdefault(section, {})
        scaled = max(1, int(default * scale))
        current = sec.get(key)
        if current is None:
            sec[key] = scaled
        else:
            # Respect user ceiling: never scale up beyond what they set
            sec[key] = min(current, scaled)

    _apply("home_region",    "max_fm_per_state",        150)
    _apply("home_region",    "max_dmr_per_state",       100)
    _apply("adjacent_region","max_fm_per_state",         30)
    _apply("adjacent_region","max_dmr_freqs_per_state",   5)
    _apply("adjacent_region","dmr_tgs_per_freq",          3)
    _apply("shallow_region", "max_fm_freqs",             10)
    _apply("shallow_region", "max_dmr_freqs",             3)

    return config


def organize_zones_tiered(
    repeaters: list[Repeater],
    state_tiers: dict[str, str],
    ctcss_map: dict,
    input_freq_map: dict,
    config: dict,
    state_tg_map: dict[str, int],
    max_channels: int = MAX_CHANNELS,
    max_channels_per_zone: int = MAX_CHANNELS_PER_ZONE,
) -> list[dict]:
    """Build the full ordered zone spec list for the tiered_region strategy.

    Order: home_state (band-split) → other home alphabetical → adjacent alphabetical
           → shallow alphabetical → Simplex.
    """
    from .api import US_STATES as _US_STATES

    effective_zone_max = min(MAX_CHANNELS_PER_ZONE, max_channels_per_zone)
    zone_specs: list[dict] = []
    home_state = config.get("home_state", "MO")

    home_states   = sorted(s for s, t in state_tiers.items() if t == "home")
    adjacent_states = sorted(s for s, t in state_tiers.items() if t == "adjacent")
    shallow_states  = sorted(s for s, t in state_tiers.items() if t == "shallow")

    # Primary home state: split 2m / 70cm
    if home_state in state_tiers:
        hs_rpts = [r for r in repeaters if r.state_abbr == home_state]
        hs_ch = home_state_channels(home_state, hs_rpts, config, state_tg_map)
        ch_2m   = [ch for ch in hs_ch if 144.0 <= ch["rx_freq"] <= 148.0]
        ch_70cm = [ch for ch in hs_ch if 420.0 <= ch["rx_freq"] <= 450.0]
        _add_zone_with_overflow(zone_specs, f"{home_state} 2m",   ch_2m,   "home", home_state, effective_zone_max)
        _add_zone_with_overflow(zone_specs, f"{home_state} 70cm", ch_70cm, "home", home_state, effective_zone_max)
        log.info(f"{home_state} (home/primary): {len(hs_ch)} channels ({len(ch_2m)} 2m, {len(ch_70cm)} 70cm)")

    # Other home states
    for state in home_states:
        if state == home_state:
            continue
        st_rpts = [r for r in repeaters if r.state_abbr == state]
        st_ch = home_state_channels(state, st_rpts, config, state_tg_map)
        _add_zone_with_overflow(zone_specs, state, st_ch, "home", state, effective_zone_max)
        log.info(f"{state} (home): {len(st_ch)} channels")

    # Adjacent states
    for state in adjacent_states:
        st_rpts = [r for r in repeaters if r.state_abbr == state]
        st_ch = adjacent_state_channels(state, st_rpts, ctcss_map, input_freq_map, config)
        _add_zone_with_overflow(zone_specs, state, st_ch, "adjacent", state, effective_zone_max)
        log.info(f"{state} (adjacent): {len(st_ch)} channels")

    # Shallow states
    for state in shallow_states:
        st_rpts = [r for r in repeaters if r.state_abbr == state]
        st_ch = shallow_state_channels(state, st_rpts, ctcss_map, input_freq_map, config)
        _add_zone_with_overflow(zone_specs, state, st_ch, "shallow", state, effective_zone_max)
        log.info(f"{state} (shallow): {len(st_ch)} channels")

    # Simplex
    simplex_ch = generate_simplex_channels(config)
    if simplex_ch:
        zone_specs.append({
            "name": "Simplex",
            "tier": "simplex",
            "state": "",
            "channels": simplex_ch,
        })

    total_ch = sum(len(zs["channels"]) for zs in zone_specs)
    log.info(f"Total zones: {len(zone_specs)}, total channels: {total_ch}")
    if total_ch > max_channels:
        log.warning(f"WARNING: {total_ch} channels exceeds radio limit of {max_channels}!")

    return zone_specs
