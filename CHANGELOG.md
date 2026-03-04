# Changelog

All notable changes to plugsmith will be documented here.

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
