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
- **DMR talkgroup fetching** — pulls live TG lists from BrandMeister and TGIF; fills your radio's full contact capacity (up to 10,000 TGs) and uses actual per-repeater TS1/TS2 assignments from RadioID instead of generic defaults
- **Write, read, verify, encode, decode** directly to/from your radio via dmrconf — plus offline YAML↔DFU conversion and callsign DB programming
- **Live streaming output** — see every API fetch and dmrconf log line as it happens
- **In-app config editor** — change callsign, location, filters without leaving the TUI
- **Roaming Zones** — define a driving route or radius zone; plugsmith finds matching repeaters from cached data and generates named zones on next build
- **First-run wizard** — guided setup on first launch
- **Cross-platform** — macOS, Linux, Windows (WSL)
- **Multi-mode support** — FM and DMR stable; System Fusion repeaters included as FM-analog channels on all radios; P-25, NXDN, M17, Tetra scaffolded
- **Any dmrconf-compatible radio** — Anytone, TYT, Radioddity, Baofeng, and more
- **Generic hardware config editor** — auto-generates an editable form from any `{model}_settings` YAML block for unsupported radios

## Requirements

- Python 3.11+
- [`dmrconf`](https://dm3mat.darc.de/qdmr/) installed and on your PATH
- A codeplug `config.yaml` (plugsmith can create a starter one)
- **RepeaterBook API access** — see below

## RepeaterBook API Access

plugsmith fetches repeater data from [RepeaterBook](https://www.repeaterbook.com). As of March 3, 2026, API access requires **allowlist approval** from RepeaterBook — it is **not** granted automatically by creating a website account, and unapproved User-Agents are denied outright.

**Free for non-commercial use** (hobby, open-source, emergency communications, club, etc.).

### How to request access

1. Fill out the request form at **[repeaterbook.com/api/token_request.php](https://www.repeaterbook.com/api/token_request.php)**
2. Select a project category (e.g. "Hobby" or "Open Source")
3. Describe your intended use (e.g. "Generating DMR codeplugs for personal amateur radio use with plugsmith")
4. Wait for admin approval — a RepeaterBook account is not required to submit, but approval is not instant

### Current auth: email in User-Agent

Once approved, set your contact email in `config.yaml`:

```yaml
api_email: you@example.com
```

plugsmith includes this in its HTTP User-Agent header as required by RepeaterBook's terms. **Generic or fake email addresses will receive a 401 response.** All repeater data is cached locally for 30 days, so the API is only contacted when the cache is stale.

### Upcoming: token-based authentication

RepeaterBook is targeting a token-based authentication system for rollout by **March 31, 2026**, after which the current allowlist-only approach will be phased out. The token request form above is the entry point — admin approval is required before any token is issued.

Two token types will exist: `app_...` tokens (default, no RepeaterBook account needed) and `usr_...` tokens (for users with a mapped RepeaterBook account). The transmission mechanism (which header or parameter carries the token) has not yet been published. plugsmith will add token support once the specification is released.

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
| **Radio** | Detect, read (.yaml/.dfu/.csv), write, verify, encode/decode, callsign DB |
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

> **Note:** Yaesu System Fusion and Icom D-STAR radios are not supported by dmrconf. plugsmith cannot write codeplugs to these radios.

## Supported Modes

plugsmith selects repeater modes based on your radio's hardware capabilities and your
`config.yaml` `modes:` block. Only modes your radio physically supports are available.

| Mode | Status | Notes |
|------|--------|-------|
| FM Analog | ✅ Stable | Full support — analog channels with CTCSS |
| DMR | ✅ Stable | Full support — digital channels with talkgroups |
| System Fusion (C4FM) | ✅ Supported | C4FM/Fusion repeaters are backward-compatible FM. plugsmith includes them as FM-analog channels on all radios when `modes.fusion: true`. Note: Yaesu FT3D/FT5D radios cannot be programmed via dmrconf. |
| D-Star | ❌ Not supported | D-STAR is not supported by dmrconf. Icom D-STAR radios cannot be programmed via plugsmith. |
| APCO P-25 | 🔧 Scaffolded | Repeater data parsed and filtered; no channels generated yet. |
| NXDN | 🔧 Scaffolded | Repeater data parsed and filtered; no channels generated yet. |
| M17 | 🔧 Scaffolded | Repeater data parsed and filtered; no channels generated yet. |
| Tetra | 🔧 Scaffolded | Repeater data parsed and filtered; no channels generated yet. |

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
