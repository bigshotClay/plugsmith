# plugsmith builder

The builder pipeline converts RepeaterBook repeater data into a qdmr-compatible codeplug YAML, with optional DMR talkgroup enrichment from BrandMeister, TGIF, and RadioID.

## Pipeline

```
1. Load config (build_config.py)
2. Detect radio profile (tool_discovery.py)
3. Fetch repeaters from RepeaterBook (api.py)
4. Parse + deduplicate repeaters (filters.py)
5. Filter by mode, band, status (filters.py)
6. Calculate distances from reference location (filters.py)
7. Classify states into tiers: home / adjacent / shallow (filters.py)
8. [NEW] Fetch TG registry from BrandMeister + TGIF (talkgroups.py)
9. [NEW] Fetch RadioID per-repeater TG assignments for home states (talkgroups.py)
10. Build CTCSS and input frequency maps (filters.py)
11. Organize tiered zones → zone specs (zones.py)
12. Generate qdmr YAML codeplug (codeplug.py)
13. Write outputs: codeplug.yaml, anytone_csv/, codeplug_summary.txt (export.py)
```

Steps 8–9 are new. Both use the same cache-on-first-use pattern as the RepeaterBook client (24-hour TTL, stale-cache fallback on network error, progress callbacks for the TUI).

---

## Talkgroup Fetching (talkgroups.py)

### TalkgroupClient

Fetches DMR talkgroup lists from BrandMeister and TGIF, merges them into a `TalkgroupRegistry`.

```python
from plugsmith.builder.talkgroups import TalkgroupClient

client = TalkgroupClient(
    cache_dir=".rb_cache",
    rate_limit=2.0,
    user_agent="plugsmith/1.0 (you@example.com)",
    progress_callback=lambda msg, is_cached: print(msg),
)
registry = client.fetch_registry(networks=["brandmeister", "tgif"])
print(registry.name(9))    # "Local"
print(len(registry))       # number of unique TGs merged
```

**Cache files**: `{cache_dir}/tg_brandmeister.json`, `{cache_dir}/tg_tgif.json`
**TTL**: 7 days
**Merge priority**: BrandMeister wins on ID conflict (larger, more authoritative network)

### RadioIDClient

Fetches per-repeater static talkgroup assignments from RadioID.net by state.

```python
from plugsmith.builder.talkgroups import RadioIDClient

client = RadioIDClient(cache_dir=".rb_cache", rate_limit=2.0)
tg_map = client.fetch_states(["MO", "IL"])
# tg_map: dict[callsign (uppercase) → RepeaterTGData]

data = tg_map.get("W0RRK")
if data:
    print(data.ts1_static)  # e.g. [9, 3129, 8]
    print(data.ts2_static)  # e.g. [3100, 93, 310, 311]
```

**Cache files**: `{cache_dir}/radioid_{STATE}.json` (e.g. `radioid_MO.json`)
**TTL**: 7 days
**API**: `GET https://radioid.net/api/dmr/repeater/?state={full_state_name}`

### TalkgroupRegistry

Merged lookup table produced by `TalkgroupClient.fetch_registry()`.

```python
registry.name(tg_id)       # str — falls back to zones.tg_name() for unknowns
registry.call_type(tg_id)  # "GroupCall" | "PrivateCall"
registry.all_tgs()         # list[TalkgroupInfo]
len(registry)              # number of unique TGs
tg_id in registry          # membership test
```

---

## Per-Repeater TG Assignment (zones.py)

`home_state_channels()` now accepts an optional `repeater_tg_map` parameter:

```python
channels = home_state_channels(
    state="MO",
    state_repeaters=repeaters,
    config=config,
    state_tg_map=state_tg_map,
    repeater_tg_map=radioid_tg_map,   # dict[callsign → RepeaterTGData] or None
)
```

**With RadioID data present for a repeater**: TS1 and TS2 channel slots use the repeater's actual registered TG assignments from RadioID, capped by `dmr_talkgroups_per_repeater`.

**Without RadioID data** (repeater not in map, or `repeater_tg_map=None`): falls back to hardcoded BrandMeister defaults (TS1: Local/Regional/State, TS2: US National/NAm/TAC310/TAC311).

The `dmr_talkgroups_per_repeater` cap applies in both cases. Budget split: TS1 fills up to `max//2` slots, TS2 fills the remainder.

---

## Contact List Filling (codeplug.py)

`generate_codeplug_yaml()` accepts two new optional parameters:

```python
codeplug = generate_codeplug_yaml(
    zone_specs=zone_specs,
    dmr_id=dmr_id,
    callsign=callsign,
    tg_registry=registry,      # TalkgroupRegistry or None
    radio_max_tgs=10_000,      # from radio profile; varies by radio (GD-77: 1,024; AnyTone: 10,000)
)
```

**Fill priority** (when `tg_registry` is provided):

1. In-use TGs (referenced by channels) — always first
2. Core BrandMeister TGs: 1, 2, 3, 8, 9, 13, 91, 93, 310, 311, 312, 3100, 9998, 4000
3. State TGs for all 50 states (`STATE_TGS_DEFAULT` values)
4. Full registry sorted by TG ID — until `radio_max_tgs` is reached

**Group lists**: `gl_all` contains only in-use TGs (channel-referenced), not the entire filled contact list. This keeps scan and group lists at a usable size.

---

## config.yaml Reference

```yaml
talkgroups:
  # DMR talkgroup registries to fetch (names and descriptions for all TGs).
  # "brandmeister" — BrandMeister API v2, no auth required, excellent USA coverage
  # "tgif"         — TGIF Network API, no auth required, ~2,925 talkgroups
  networks:
    - brandmeister
    - tgif

  # Fill the radio's DMR contact list up to its hardware limit (e.g. 10,000 for
  # AT-D878UVII) with named TGs from the registry. In-use TGs are always included.
  fill_contacts: true

  # Use RadioID per-repeater static TG assignments for home-tier DMR channel
  # generation instead of hardcoded BrandMeister defaults. Falls back to defaults
  # when RadioID has no record for a repeater.
  per_repeater_lookup: true
```

All three keys default to the values shown. Set `fill_contacts: false` and `per_repeater_lookup: false` to disable TG fetching entirely and restore pre-feature behavior.

---

## Radio Capacity Utilization

| Resource     | Before (hardcoded) | After (with registry) |
|--------------|--------------------|-----------------------|
| Channels     | 4,000 / 4,000      | 4,000 / 4,000         |
| TG Contacts  | ~30 / 10,000       | up to 10,000 / 10,000 |
| TG Names     | 28 hardcoded       | Live from registry    |
| Per-repeater | 7 generic TG slots | Actual RadioID TGs    |

---

## Cache Layout

```
.rb_cache/
  state_*.json          RepeaterBook per-state cache (30-day TTL)
  tg_brandmeister.json  BrandMeister TG registry (7-day TTL)
  tg_tgif.json          TGIF TG registry (7-day TTL)
  radioid_MO.json       RadioID per-repeater data for Missouri (7-day TTL)
  radioid_IL.json       RadioID per-repeater data for Illinois (7-day TTL)
  ...
  geocode_cache.json    Nominatim geocode results (roaming zones)
```

The "Clear Cache" button in the Build tab clears all cache files including the new TG caches.
