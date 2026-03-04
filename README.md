# plugsmith

> Terminal UI for managing DMR radio codeplugs with dmrconf

plugsmith bundles a complete codeplug builder (pulls repeater data from RepeaterBook and generates qdmr-compatible YAML) and wraps `dmrconf` for radio I/O — all in a single keyboard-driven terminal app.

```
┌─ plugsmith ─────────────────────────────────────────────────────────┐
│  Dashboard | Build | Radio | Config                                  │
├─────────────────────────────────────────────────────────────────────┤
│  Codeplug Status                                                     │
│  Codeplug:   /home/user/ham/codeplug.yaml                           │
│  Channels:   4000 / 4000                                            │
│  Zones:      71                                                      │
│  Last built: 2026-03-03 10:42                                       │
└─────────────────────────────────────────────────────────────────────┘
```

## Features

- **Build codeplugs from RepeaterBook** — all 50 states, tiered by distance from your QTH
- **Write, read, verify** directly to your radio via dmrconf
- **Live streaming output** — see every API fetch and dmrconf log line as it happens
- **In-app config editor** — change callsign, location, filters without leaving the TUI
- **Roaming Zones** — define a driving route or radius zone; plugsmith finds matching repeaters from cached data and generates named zones on next build
- **First-run wizard** — guided setup on first launch
- **Cross-platform** — macOS, Linux, Windows (WSL)
- **Any dmrconf-compatible radio** — Anytone, TYT, Radioddity, Baofeng, and more

## Requirements

- Python 3.11+
- [`dmrconf`](https://dm3mat.darc.de/qdmr/) installed and on your PATH
- A codeplug `config.yaml` (plugsmith can create a starter one)

## Install

```bash
pip install plugsmith
```

## Quick Start

```bash
plugsmith            # launch the TUI (setup wizard on first run)
plugsmith --help     # CLI options
```

## First Run

On first launch plugsmith shows a 3-step wizard:

1. **Locate config** — point to an existing `config.yaml` or create a new one
2. **Radio setup** — enter device path and select radio model
3. **Confirm** — review settings and save

After the wizard, you're dropped into the main interface with four tabs:

| Tab | What it does |
|-----|-------------|
| **Dashboard** | Codeplug stats + quick-launch buttons |
| **Build** | Fetch RepeaterBook data and generate codeplug.yaml |
| **Radio** | Detect, read, write, and verify with dmrconf |
| **Config** | Edit config.yaml fields in-app |
| **Roaming** | Add/edit/delete roaming zone definitions |

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Ctrl+Q` | Quit |
| `Ctrl+B` | Jump to Build tab |
| `Ctrl+R` | Jump to Radio tab |
| `Ctrl+E` | Jump to Config tab |
| `Ctrl+G` | Jump to Roaming tab |
| `F1` | Help |

## Supported Radios

Any radio supported by dmrconf. Common models:

- Anytone AT-D878UVII, AT-D878UV, AT-D868UV, AT-D578UV
- TYT MD-UV390, MD-380, MD-390
- Radioddity GD-77, GD-73
- Baofeng DM-1801

## Device Path Notes

**macOS:** `cu.usbmodem0000000100001` (no `/dev/` prefix in dmrconf)
**Linux:** `/dev/ttyUSB0` or similar
**WSL:** `/dev/ttyS0` (requires usbipd-win)

## Write Quirk

When writing to radio, dmrconf shows `[0%]` then exits with "Upload completed" — **this is success**. The radio reboots immediately. Do not run write again.

## Troubleshooting

See [docs/troubleshooting.md](docs/troubleshooting.md) or [open an issue](https://github.com/yourusername/plugsmith/issues).

## License

MIT — see [LICENSE](LICENSE).
