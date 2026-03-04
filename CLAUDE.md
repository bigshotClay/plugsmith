# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project

**plugsmith** — open-source TUI for DMR codeplug management, built on
[Textual](https://textual.textualize.io/) and [dmrconf](https://dm3mat.darc.de/qdmr/).
Refactored from the companion `codeplug` repo's builder script.

## Environment

- **Python**: 3.11+ required (uses `tomllib` from stdlib)
- **Venv**: `.venv/` — always use `.venv/bin/python` / `.venv/bin/pytest`
- **Install**: `pip install -e ".[dev]"` from repo root
- **Run tests**: `.venv/bin/pytest` (or `pytest` if venv is activated)
- **Run app**: `.venv/bin/plugsmith`

## Key Files

```
src/plugsmith/
  app.py               — PlugsmithApp + main()
  config.py            — PlugsmithConfig dataclass (toml-backed)
  runner.py            — SubprocessRunner mixin (dmrconf subprocess)
  tool_discovery.py    — find_dmrconf(), list_radio_models(), RadioProfile, RADIO_PROFILES
  builder/
    api.py             — RepeaterBookClient
    models.py          — Repeater, Channel dataclasses
    filters.py         — parse_repeaters, filter_repeaters, classify_states
    zones.py           — organize_zones_tiered, scale_config_to_radio, STATE_TGS_DEFAULT
    codeplug.py        — generate_codeplug_yaml
    export.py          — write_qdmr_yaml, write_anytone_csv, write_summary
    build_config.py    — load_config, DEFAULT_CONFIG
    roaming.py         — geocoding, routing, roaming zone generation
  screens/
    main_screen.py     — MainScreen, DashboardPane
    build_screen.py    — BuildPane (runs builder in thread)
    radio_screen.py    — RadioPane (dmrconf subprocess)
    config_editor.py   — ConfigEditorPane
    setup_wizard.py    — SetupWizardScreen
    modals.py          — ConfirmModal, ErrorModal, FilePickerModal, WriteAcknowledgeModal
    roaming_screen.py  — RoamingPane (Roaming tab)
    roaming_zone_modal.py — RoamingZoneModal (3-step add/edit modal)
  widgets/
    output_log.py      — RichLog + autoscroll
    status_bar.py      — persistent status bar
    field_editors.py   — LabeledInput, LabeledSwitch
tests/
  conftest.py          — shared fixtures
  test_radio_profiles.py
  test_scale_config.py
  test_codeplug_hw.py
  test_zones_overflow.py
  test_tool_discovery.py
  test_config.py
  test_runner.py
```

## Development Methodology: Test-Driven Development

**All new features and bug fixes must be developed using TDD.**

### TDD Workflow

1. **Write the test first.** Before writing any implementation code, write a failing test
   that describes the expected behavior.
2. **Run and confirm it fails.** The test must fail (red) before you write any code.
3. **Write the minimum code** to make the test pass.
4. **Run tests and confirm green.**
5. **Refactor** if needed, keeping tests green throughout.

### Coverage Requirement

- Every new module, function, and branch must have corresponding tests.
- Target: **100% coverage** for `builder/` and `tool_discovery.py`.
- Textual UI code (`screens/`, `widgets/`) is exempt from coverage requirements
  (requires a running app event loop), but logic extracted into pure functions must be tested.

### Test File Conventions

- One test file per source module: `tests/test_<module_name>.py`
- Use `pytest` fixtures in `conftest.py` for shared setup (fake repeaters, sample configs, etc.)
- Never test implementation details — test observable behavior and return values
- Name tests `test_<what_it_does>` — the name should read like a sentence

### Running Tests

```bash
# Run all tests
.venv/bin/pytest

# Run with coverage report
.venv/bin/pytest --cov=src/plugsmith --cov-report=term-missing

# Run a specific file
.venv/bin/pytest tests/test_scale_config.py -v

# Run and stop on first failure
.venv/bin/pytest -x
```

### Known Pre-Existing Test Failures

- `tests/test_runner.py` — fails due to `textual.worker.work` import path change
  in newer Textual versions. These are pre-existing and not caused by builder changes.

## Architecture Notes

- `builder/` modules are **pure Python** with no Textual dependency — always testable
- `screens/` and `widgets/` depend on Textual — test by extracting logic into `builder/`
- Builder runs **in-process** in a `@work(thread=True)` worker — not a subprocess
- `SubprocessRunner` wraps dmrconf; drains stdout+stderr concurrently in two threads
- `call_from_thread` used for all UI updates from worker threads

## Radio Capability Registry

`tool_discovery.RADIO_PROFILES` maps dmrconf model keys to `RadioProfile` dataclasses.
`scale_config_to_radio()` in `builder/zones.py` scales channel caps proportionally.
`generate_codeplug_yaml()` in `builder/codeplug.py` uses `hw_settings_key` to route
hardware settings to the correct qdmr YAML key (strips `_settings` suffix).

## dmrconf Write Quirk

`[0%]` then "Upload completed" with exit 0 = **success**. Do NOT re-run.
