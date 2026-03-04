# Contributing to plugsmith

Thanks for your interest in contributing! This document covers development setup,
architecture, code style, and how to submit changes.

## Development Setup

```bash
git clone https://github.com/yourusername/plugsmith
cd plugsmith
pip install -e ".[dev]"

# Launch with live reload (Textual devtools)
textual run --dev src/plugsmith/app.py

# Run tests
pytest tests/
```

## Architecture Overview

```
plugsmith/
├── src/plugsmith/
│   ├── app.py              # PlugsmithApp root class + main() entry point
│   ├── config.py           # PlugsmithConfig dataclass (NOT the codeplug config)
│   ├── runner.py           # SubprocessRunner mixin — streams dmrconf output
│   ├── tool_discovery.py   # Find dmrconf binary, list radio models
│   ├── builder/            # Bundled codeplug builder (no subprocess needed)
│   │   ├── api.py          # RepeaterBook API client + file-based caching
│   │   ├── models.py       # Repeater, Channel dataclasses
│   │   ├── filters.py      # parse_repeaters, filter_repeaters, classify_states
│   │   ├── zones.py        # organize_zones_tiered + legacy strategies
│   │   ├── codeplug.py     # generate_codeplug_yaml → qdmr YAML dict
│   │   ├── export.py       # write_qdmr_yaml, write_anytone_csv, write_summary
│   │   ├── build_config.py # load_config, DEFAULT_CONFIG
│   │   └── roaming.py      # geocoding (Nominatim), routing (OSRM), roaming zone generation
│   ├── screens/
│   │   ├── main_screen.py     # MainScreen with TabbedContent (5 tabs)
│   │   ├── build_screen.py    # BuildPane: calls builder in @work(thread=True)
│   │   ├── radio_screen.py    # RadioPane: dmrconf operations via SubprocessRunner
│   │   ├── config_editor.py   # ConfigEditorPane: YAML round-trip editor
│   │   ├── setup_wizard.py    # SetupWizardScreen: 3-step first-run modal
│   │   ├── modals.py          # ConfirmModal, ErrorModal, FilePickerModal
│   │   ├── roaming_screen.py  # RoamingPane: list/add/edit/delete roaming zone defs
│   │   └── roaming_zone_modal.py # RoamingZoneModal: 3-step add/edit modal
│   ├── widgets/
│   │   ├── output_log.py   # RichLog + Clear + auto-scroll toggle
│   │   ├── status_bar.py   # Persistent status row (dmrconf health, config, radio)
│   │   └── field_editors.py# LabeledInput, LabeledSwitch reusable rows
│   └── styles/
│       └── plugsmith.tcss  # All Textual CSS
```

### External APIs used by roaming.py

- **Nominatim** (`nominatim.openstreetmap.org`) — geocoding city names to lat/lon. No auth required. Results cached in `.rb_cache/geocode_cache.json`.
- **OSRM** (`router.project-osrm.org`) — driving route geometry. No auth required. Results cached in `.rb_cache/route_{hash}.json`. Falls back to linear interpolation if unavailable.

### Key design decisions

- **Builder runs in-process** via `@work(thread=True)` — no subprocess overhead,
  real per-state progress events, typed exceptions.
- **dmrconf runs via subprocess** — it's a C++ binary; `SubprocessRunner` drains
  stdout/stderr concurrently so neither pipe can block the event loop.
- **No `builder_script` path** — the builder is bundled; users only need dmrconf.
- **Single persistent `MainScreen`** — no deep screen stacks. Modals only for
  decisions that block proceeding (write confirmation, errors).
- **`PlugsmithConfig` ≠ codeplug config** — plugsmith's own settings live at
  `~/.config/plugsmith/config.toml`; the user's codeplug settings stay in their
  `config.yaml`.

## Adding a New Screen

1. Create `src/plugsmith/screens/my_screen.py` with a `Widget` subclass
2. Add a `TabPane` to `MainScreen.compose()` in `main_screen.py`
3. Add a keybinding to `MainScreen.BINDINGS`
4. Add CSS to `plugsmith.tcss`

## Adding a New Builder Feature

All builder logic lives in `src/plugsmith/builder/`. Add or modify the appropriate
module, then update `BuildPane._run_build()` to call it and post progress messages.

## Code Style

- **Black** formatting (`pip install black && black src/`)
- **isort** imports (`pip install isort && isort src/`)
- Type hints required on all public functions and methods
- Textual CSS goes in `plugsmith.tcss` only — no inline styles
- Post `Message` objects for cross-widget communication; avoid direct widget references across pane boundaries

## Running Tests

```bash
pytest tests/
pytest tests/ -v               # verbose
pytest tests/ --tb=short       # compact tracebacks
```

## Submitting a PR

1. **Open an issue first** for non-trivial changes
2. Create a branch: `git checkout -b feat/my-feature`
3. Write code + tests
4. Run `pytest tests/` — all tests must pass
5. Update `docs/` if user-visible behavior changes
6. Add an entry to `CHANGELOG.md`
7. Open the PR — the template will guide you through the checklist
