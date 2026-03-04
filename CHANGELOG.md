# Changelog

All notable changes to plugsmith will be documented here.

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
