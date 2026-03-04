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
| `init_codeplug` | bool | `true` | Pass `--init-codeplug` on write |
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
last_tab = "tab-build"
```

## Codeplug config: `config.yaml`

Your personal codeplug settings. Edited in the Config tab or directly.

Key fields:

| Key | Description |
|-----|-------------|
| `dmr_id` | Your DMR ID number (register at radioid.net) |
| `callsign` | Your amateur radio callsign |
| `api_email` | **Required.** Your email address — sent in the RepeaterBook API User-Agent header per their ToS. Generic or fake values get 401. |
| `reference_location.lat/lon` | Your QTH coordinates for distance calculations |
| `home_state` | Your home state (gets extra 2m/70cm zone splitting) |
| `organization.strategy` | `tiered_region` (recommended), `state_band`, `state_county`, `distance_rings` |
| `tiers.home_radius_miles` | States within this distance get full per-repeater coverage |
| `tiers.adjacent_radius_miles` | States within this distance get top-N coverage |
| `modes.fm` / `modes.dmr` | Enable/disable analog FM and DMR digital |
| `bands` | List of bands: `2m`, `70cm` |
| `filters.open_only` | Only include OPEN repeaters |
| `filters.on_air_only` | Only include On-air repeaters |
| `rate_limit_seconds` | Seconds between RepeaterBook API requests (min 5.0) |
| `cache_dir` | Directory for RepeaterBook JSON cache files |

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
| `max_channels` | both | int | radio max | Optional per-zone channel cap |

Location strings accept city names (`"Chicago, IL"`) or raw coordinates (`"41.85,-87.65"`).
See [docs/roaming-zones.md](roaming-zones.md) for full documentation.

### anytone_settings

The `anytone_settings` block contains radio-specific hardware settings
(boot display, key functions, audio, DMR timing, etc.). These are written
directly to the `settings.anytone` block in codeplug.yaml.

plugsmith's Config tab does **not** expose `anytone_settings` — edit
`config.yaml` directly for these values. See the example config.yaml in
the codeplug repo for all available fields.

## Radio model keys

Common dmrconf radio keys (first column in `dmrconf --list-radios`):

| Key | Radio |
|-----|-------|
| `d878uv2` | Anytone AT-D878UVII |
| `d878uv` | Anytone AT-D878UV |
| `d868uv` | Anytone AT-D868UV |
| `d578uv` | Anytone AT-D578UV |
| `uv390` | TYT MD-UV390 |
| `md380` | TYT MD-380 |
| `gd77` | Radioddity GD-77 |
