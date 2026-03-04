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
- **Multi-mode support** — FM and DMR stable; System Fusion (Yaesu) and D-Star (Icom) experimental; P-25, NXDN, M17, Tetra scaffolded
- **Any dmrconf-compatible radio** — Anytone, TYT, Radioddity, Yaesu, Icom, Baofeng, and more

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
- Yaesu FT3D, FT5D *(System Fusion — experimental)*
- Icom ID-51, ID-52 *(D-Star — experimental)*

## Supported Modes

plugsmith selects repeater modes based on your radio's hardware capabilities and your
`config.yaml` `modes:` block. Only modes your radio physically supports are available.

| Mode | Status | Notes |
|------|--------|-------|
| FM Analog | ✅ Stable | Full support — analog channels with CTCSS |
| DMR | ✅ Stable | Full support — digital channels with talkgroups |
| System Fusion (C4FM) | ⚠️ Experimental | Channels generated as analog; requires Fusion-capable radio (Yaesu FT3D, FT5D, etc.). Not hardware-tested — please [submit a report](#hardware-submission) if you use this. |
| D-Star | ⚠️ Experimental | Basic channel generation; requires D-Star-capable radio (Icom ID-51, ID-52, etc.). qdmr YAML format unverified against real hardware — please [submit a report](#hardware-submission). |
| APCO P-25 | 🔧 Scaffolded | Repeater data parsed and filtered; no channels generated yet. |
| NXDN | 🔧 Scaffolded | Repeater data parsed and filtered; no channels generated yet. |
| M17 | 🔧 Scaffolded | Repeater data parsed and filtered; no channels generated yet. |
| Tetra | 🔧 Scaffolded | Repeater data parsed and filtered; no channels generated yet. |

**Experimental modes** have been implemented based on the qdmr YAML specification but
have not been tested against real hardware + dmrconf. If your radio supports one of
these modes, please use the Hardware Submission feature to send us a working config
so we can promote it to stable.

## Hardware Submission

When you configure an **unsupported radio model** in plugsmith (one not in the built-in
profile list), the app will offer to submit a hardware config report on your behalf.

### What it does

1. Detects that your radio key is not in the known-radios list
2. Prompts you once (not on every launch) to send a config report
3. Posts a GitHub Issue to the plugsmith repository containing:
   - Your radio model key and display name
   - Your firmware version
   - Your `hw_settings:` block from `config.yaml` (radio-specific parameters)
   - Any notes you choose to add
   - The dmrconf version you are using

### What it does NOT send

- Your DMR ID, callsign, or personal information
- Your RepeaterBook data or codeplug contents
- Any files from your system

### Why this helps

Hardware reports let maintainers add verified radio profiles with correct channel/zone
limits and mode support flags. Each submission can unlock full support for a radio
model that was previously unsupported or experimental.

### Opting out

Simply dismiss the prompt — plugsmith records that you declined and will not ask again
for the current radio+firmware combination. No data is ever sent without your explicit
action.

## Device Path Notes

**macOS:** `cu.usbmodem0000000100001` (no `/dev/` prefix in dmrconf)
**Linux:** `/dev/ttyUSB0` or similar
**WSL:** `/dev/ttyS0` (requires usbipd-win)

## Write Quirk

When writing to radio, dmrconf shows `[0%]` then exits with "Upload completed" — **this is success**. The radio reboots immediately. Do not run write again.

## Troubleshooting

See [docs/troubleshooting.md](docs/troubleshooting.md) or [open an issue](https://github.com/bigshotClay/plugsmith/issues).

## License

MIT — see [LICENSE](LICENSE).
