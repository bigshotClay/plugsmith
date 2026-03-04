# Changelog

All notable changes to plugsmith will be documented here.

## [0.5.0] — 2026-03-04

### Added
- **Radio Hardware Settings UI** — the Config tab now exposes all 75 AnyTone hardware settings in a collapsible "Radio Hardware Settings (AnyTone)" section
  - Settings organized into 8 groups: Boot, Power Save, Programmable Keys, Tones & Alerts, Display, Audio, DMR, GPS
  - Each setting shows description, ham-preferred value, and safety warnings where applicable
  - Critical warnings for: encryption (FCC Part 97.113 violation on ham bands), P6 key encryption shortcut, boot password, cooling fan Off setting
  - Widget type matches setting type: Switch (bool), Select (enum), Input (int/str)
  - Values read from and written back to `config.yaml`'s `anytone_settings` block on save
- `builder/radio_settings_meta.py` — new module with `SettingMeta` dataclass and `ANYTONE_SETTINGS` catalog (75 settings, 8 groups)
- Full test coverage for all new and existing builder modules (100% for `builder/`)

## [0.4.0] — 2026-03-04

### Added
- **Radio tab: Read .csv** — export radio codeplug to Anytone CPS CSV format
- **Radio tab: Info** — display codeplug.yaml summary offline (channel count, zones, TGs) via `dmrconf info`
- **Radio tab: Format Conversion collapsible** — encode YAML → DFU and decode DFU → YAML without a connected radio
- **Radio tab: Callsign Database collapsible** — write DMR ID callsign DB to radio (`write-db`) or encode to file (`encode-db`)
- **Write Options collapsible** — four toggles controlling write flags: Init codeplug, Sync device clock, Auto-enable GPS, Auto-enable roaming. Switch state persists to `config.toml` on every toggle
- **WriteAcknowledgeModal** — two-gate safety flow before write: acknowledge experimental status + confirm backup exists (checkbox required), then confirm specific write operation
- 5 new `config.toml` fields: `update_device_clock`, `auto_enable_gps`, `auto_enable_roaming`, `callsign_db_path`, `callsign_limit`

### Fixed
- `--init-codeplug` write flag was hardcoded; now reads from the Write Options toggle (respects `init_codeplug` config field)

## [0.3.0] — 2026-03-04

### Added
- **Dynamic DMR talkgroup fetching** — new `builder/talkgroups.py` module with two API clients:
  - `TalkgroupClient`: fetches BrandMeister (`/v2/talkgroup`) and TGIF (`/dmr/talkgroups/json`) TG registries; merges them with BrandMeister taking priority on conflicts
  - `RadioIDClient`: fetches per-repeater static TS1/TS2 talkgroup assignments from RadioID (`/api/dmr/repeater/?state=…`) for all home-tier states
- **Contact list fill**: codeplug now populates the radio's full DMR contact capacity (e.g. 10,000 on AT-D878UVII, up from ~30) using fetched TG data, in priority order: in-use TGs → core TGs → state TGs → full registry
- **Per-repeater TG assignment**: home-tier DMR channels use RadioID's registered TS1/TS2 static TG lists when available, falling back to hardcoded BrandMeister defaults when not
- `talkgroups:` config section in `config.yaml` with three keys: `networks`, `fill_contacts`, `per_repeater_lookup` (all enabled by default)
- `max_talkgroups` field on `RadioProfile` (default 10,000)
- "Clear Cache" button now clears TG and RadioID caches in addition to RepeaterBook caches
- 47 new unit tests in `tests/test_talkgroups.py`
- `src/plugsmith/builder/README.md` — pipeline and API reference documentation

### Changed
- **Cache TTLs**: RepeaterBook caches extended from 12 hours to **30 days**; TalkgroupClient and RadioIDClient caches set to **7 days** — be kind to public APIs, use "Clear Cache" to force a refresh
- TGIF descriptions are base64-decoded and stored in the registry
- Group lists (`gl_all`) remain scoped to in-use TGs only — the full filled contact list is available for manual use without bloating channel scan lists

## [0.2.0] — 2026-03-04

### Added
- **Roaming Zones** — define route or radius zones; matched repeaters are built into the codeplug on next build
- `builder/roaming.py` — geocoding (Nominatim), routing (OSRM), corridor/radius filtering, zone spec generation
- `screens/roaming_screen.py` — Roaming tab with DataTable listing all defined zones; add/edit/delete actions
- `screens/roaming_zone_modal.py` — 3-step modal for adding/editing route and radius zone definitions
- `Ctrl+G` keyboard shortcut to jump to the Roaming tab
- `roaming_zones: []` key in `DEFAULT_CONFIG` (codeplug config)
- Geocode and route geometry caching in `.rb_cache/geocode_cache.json` and `.rb_cache/route_{hash}.json`
- OSRM fallback: linear interpolation between endpoints if routing server is unavailable
- Channel budget enforcement: roaming zones never push total over radio's `max_channels`
- Full unit test coverage for `builder/roaming.py` in `tests/test_roaming.py`
- `docs/roaming-zones.md` — full user guide

## [0.1.0] — 2026-03-03

### Added
- Initial release
- Bundled codeplug builder (RepeaterBook API client + qdmr YAML generator)
- Textual TUI with Dashboard, Build, Radio, and Config tabs
- dmrconf wrapper: detect, read (.yaml + .dfu), write, verify
- First-run setup wizard (3-step modal)
- Persistent StatusBar showing dmrconf health, config file, and radio connection
- ConfigEditorPane: edit config.yaml fields without leaving the TUI
- BuildPane: live per-state progress streaming during build
- RadioPane: write with ConfirmModal, post-write reboot notice
- FilePickerModal, ErrorModal, ConfirmModal shared modals
- ConfirmModal with `danger=True` variant for write-to-radio
- LabeledInput and LabeledSwitch reusable form row widgets
- Auto-scroll toggle on OutputLog
- GitHub issue templates (bug report, feature request)
- GitHub PR template
- PyPI publish workflow (OIDC trusted publishing)
