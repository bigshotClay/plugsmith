# Configuration

plugsmith uses two separate config files:

## plugsmith's own settings: `~/.config/plugsmith/config.toml`

Created by the setup wizard. Edit manually or use the setup wizard.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `dmrconf_path` | string | `""` | Path to dmrconf binary. Empty = auto-detect via PATH |
| `codeplug_config` | string | `""` | Path to your codeplug `config.yaml` |
| `codeplug_yaml` | string | `""` | Path to output codeplug.yaml. Default: next to config |
| `device` | string | `""` | USB device handle (e.g. `cu.usbmodem0000000100001`) |
| `radio_model` | string | `""` | dmrconf radio key (e.g. `d878uv2`) |
| `backup_dir` | string | `"backups"` | Backup directory (relative to config or absolute) |
| `init_codeplug` | bool | `true` | Pass `--init-codeplug` on write (erases radio before write — recommended) |
| `update_device_clock` | bool | `false` | Pass `--update-device-clock` on write (sync radio clock to system time) |
| `auto_enable_gps` | bool | `false` | Pass `--auto-enable-gps` on write (enable GPS if supported by radio) |
| `auto_enable_roaming` | bool | `false` | Pass `--auto-enable-roaming` on write (enable roaming if supported) |
| `callsign_db_path` | string | `""` | Path to a local callsign DB JSON file for `write-db` / `encode-db`. Empty = download from BrandMeister |
| `callsign_limit` | int | `0` | Max entries for callsign DB operations (`--limit N`). `0` = no limit |
| `last_tab` | string | `"tab-dashboard"` | Restore last active tab on launch |

Example:
```toml
dmrconf_path = ""
codeplug_config = "/home/user/ham/config.yaml"
codeplug_yaml = ""
device = "cu.usbmodem0000000100001"
radio_model = "d878uv2"
backup_dir = "backups"
init_codeplug = true
update_device_clock = false
auto_enable_gps = false
auto_enable_roaming = false
callsign_db_path = ""
callsign_limit = 0
last_tab = "tab-build"
```

## Codeplug config: `config.yaml`

Your personal codeplug settings. Edited in the Config tab or directly.

Key fields:

| Key | Description |
|-----|-------------|
| `dmr_id` | Your DMR ID number (register at radioid.net) |
| `callsign` | Your amateur radio callsign |
| `api_email` | **Required.** Your email address — sent in the RepeaterBook API User-Agent header per their terms. Generic or fake values get 401. Requires prior allowlist approval at [repeaterbook.com/api/token_request.php](https://www.repeaterbook.com/api/token_request.php). |
| `reference_location.lat/lon` | Your QTH coordinates for distance calculations |
| `home_state` | Your home state (gets extra 2m/70cm zone splitting) |
| `organization.strategy` | `tiered_region` (recommended), `state_band`, `state_county`, `distance_rings` |
| `tiers.home_radius_miles` | States within this distance get full per-repeater coverage |
| `tiers.adjacent_radius_miles` | States within this distance get top-N coverage |
| `modes.fm` | Enable analog FM channels (default `true`) |
| `modes.dmr` | Enable DMR digital channels (default `true`) |
| `modes.fusion` | Include System Fusion / C4FM repeaters as FM-analog channels (Fusion is backward-compatible FM). Works on all dmrconf-supported radios. Does **not** require a Yaesu radio — Yaesu FT3D/FT5D are not supported by dmrconf. Default `false`. |
| `modes.dstar` | **Removed.** D-STAR is not supported by dmrconf. Icom D-STAR radios cannot be programmed via plugsmith. |
| `modes.p25` / `modes.nxdn` / `modes.m17` / `modes.tetra` | Scaffolded — repeater data is parsed and filtered, but no channels are generated yet (all default `false`) |
| `bands` | List of bands: `2m`, `70cm` |
| `filters.open_only` | Only include OPEN repeaters |
| `filters.on_air_only` | Only include On-air repeaters |
| `rate_limit_seconds` | Seconds between RepeaterBook API requests (default 2.0 — do not lower below 2.0) |
| `cache_dir` | Directory for cache files (RepeaterBook, TG registry, RadioID) |

### roaming_zones

Optional list of route or radius zone definitions. Each definition is built into a
named zone on the next build, appended after the main tiered zones.

| Field | Mode | Type | Default | Description |
|-------|------|------|---------|-------------|
| `name` | both | string | required | Zone name |
| `mode` | both | `route` \| `radius` | required | Zone type |
| `waypoints` | route | list of strings | required | Start and end locations |
| `corridor_miles` | route | number | `25` | Half-width of route corridor in miles |
| `center` | radius | string | required | Center location |
| `radius_miles` | radius | number | `50` | Search radius in miles |
| `include_fm` | both | bool | `true` | Include analog FM channels |
| `include_dmr` | both | bool | `true` | Include DMR digital channels |
| `include_fusion` | both | bool | `false` | Include System Fusion channels (requires `modes.fusion: true`) |
| `max_channels` | both | int | radio max | Optional per-zone channel cap |

Location strings accept city names (`"Chicago, IL"`) or raw coordinates (`"41.85,-87.65"`).
See [docs/roaming-zones.md](roaming-zones.md) for full documentation.

### talkgroups

Controls DMR talkgroup fetching from external registries.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `networks` | list | `[brandmeister, tgif]` | Registries to fetch. `brandmeister` — BrandMeister API v2 (no auth, excellent USA coverage). `tgif` — TGIF Network (no auth, ~2,925 TGs). |
| `fill_contacts` | bool | `true` | Fill the radio's DMR contact list up to its hardware limit (e.g. 10,000 on AT-D878UVII) with named TGs from the registry. In-use TGs always come first. |
| `per_repeater_lookup` | bool | `true` | Use RadioID's per-repeater static TS1/TS2 TG assignments for home-tier DMR channel generation. Falls back to hardcoded BrandMeister defaults when RadioID has no record for a repeater. |

Example (all defaults — no action needed unless you want to disable something):
```yaml
talkgroups:
  networks:
    - brandmeister
    - tgif
  fill_contacts: true
  per_repeater_lookup: true
```

To disable TG fetching entirely and restore pre-0.3.0 behavior:
```yaml
talkgroups:
  fill_contacts: false
  per_repeater_lookup: false
```

**Cache:** TG registry files are cached for 7 days in `cache_dir`. Use the **Clear Cache** button in the Build tab to force a refresh.

### anytone_settings

The `anytone_settings` block contains radio-specific hardware settings for
AnyTone radios (boot display, programmable keys, audio, DMR timing, GPS, etc.).
These are written directly to the `settings.anytone` block in codeplug.yaml.

plugsmith's **Config tab exposes all AnyTone hardware settings** in a
collapsible "Radio Hardware Settings (AnyTone)" section. Each setting shows:

- **Description** — what the setting does
- **Ham preferred** — the recommended value for amateur radio use
- **Warning** — critical notes (e.g. encryption is prohibited on ham bands
  under FCC Part 97.113; the P6 key shortcut enables it by default)

The 75 settings are organized into 8 groups:

| Group | Count | Examples |
|-------|-------|---------|
| Boot | 5 | Boot screen, password, reset |
| Power Save | 4 | Screen timeout, cooling fan |
| Programmable Keys | 14 | P1–P6 short/long press functions |
| Tones & Alerts | 10 | DMR talk permit, TOT, ring tones |
| Display | 16 | Brightness, theme, standby display |
| Audio | 8 | Mic gain, monitor, speaker volume |
| DMR | 12 | Pre-wave delay, SMS format, encryption, talker alias |
| GPS | 5 | Interval, position reporting |

You can also edit `config.yaml` directly for these values.

## Radio model keys

Common dmrconf radio keys (first column in `dmrconf --list-radios`):

| Key | Radio | Supported Modes |
|-----|-------|----------------|
| `d878uv2` | Anytone AT-D878UVII | FM, DMR |
| `d878uv` | Anytone AT-D878UV | FM, DMR |
| `d868uv` | Anytone AT-D868UV | FM, DMR |
| `d578uv` | Anytone AT-D578UV | FM, DMR |
| `uv390` | TYT MD-UV390 | FM, DMR |
| `md380` | TYT MD-380 | FM, DMR |
| `gd77` | Radioddity GD-77 | FM, DMR |

> **Note:** Yaesu System Fusion and Icom D-STAR radios are not supported by dmrconf and cannot be programmed via plugsmith. This is a limitation of dmrconf, not plugsmith.


## Device-Specific Hardware Settings

Plugsmith supports device-specific hardware configuration blocks in `config.yaml`. For AnyTone
radios (AT-D868UV, AT-D878UV, AT-D878UVII, AT-D578UV), rich metadata is provided including
descriptions, recommended values, and compliance warnings.

For other radios, add a `{model_key}_settings` block to your config.yaml:

```yaml
# Example for a TYT MD-380 (model key: md380)
md380_settings:
  displaySettings:
    contrast: 5
    backlight: Auto
  audioSettings:
    micGain: 3
    volume: 8
```

Plugsmith will auto-detect this block when you open the Config tab and generate an editable
form based on the structure. You can also import settings from an existing codeplug YAML using
the "Import Settings from YAML…" button in the Config tab.

The settings block is preserved in config.yaml as-is; types are inferred from existing values
(bool, int, float, string). Values round-trip correctly — integers stay integers, booleans
stay booleans.
