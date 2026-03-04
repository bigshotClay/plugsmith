# Radio Operations

All radio operations are in the **Radio** tab (`Ctrl+R`).

## Pre-flight Checklist

Before writing to your radio:

- [ ] Charge the radio battery (or connect to external power)
- [ ] Read the current codeplug as a backup (Radio tab → Read .dfu)
- [ ] Make sure the codeplug.yaml exists and was built successfully
- [ ] Do not disturb the USB connection during write

## Detect

Click **Detect** to confirm the radio is connected and recognized:

```
$ dmrconf detect --device cu.usbmodem0000000100001
Device: Anytone AT-D878UVII
```

If detect fails, see [Troubleshooting](troubleshooting.md).

## Read (Backup)

**Read .dfu** — binary backup, use for restoring to radio:
```
backups/878uvii_20260303_104200.dfu
```

**Read .yaml** — human-readable backup, use for inspection:
```
backups/878uvii_20260303_104200.yaml
```

**Read .csv** — Anytone CPS CSV export:
```
backups/878uvii_20260303_104200.csv
```

Backups are auto-named with a timestamp. Location defaults to `backups/`
relative to your config.yaml.

## Info

Click **Info** to display a summary of the codeplug.yaml file (channel count, zones,
talkgroups, etc.) without touching the radio. Runs `dmrconf info codeplug.yaml` offline.

## Verify

Click **Verify** to compare codeplug.yaml against the radio's current contents
without writing. Useful to confirm a write succeeded.

## Write to Radio

> **Warning: the write operation reboots the radio. Do not disconnect USB
> or repeat the write command while the radio is rebooting.**

1. Click **⚠ Write to Radio**
2. **Acknowledge** the experimental software warning and confirm you have a backup
3. **Confirm** the specific write operation in the second dialog
4. Watch the output log — you will see `[0%]` then `Upload completed`
5. The radio reboots immediately. Wait ~10 seconds before disconnecting.

### Write Options

The **Write Options** collapsible (expanded by default) controls which flags are
passed to `dmrconf write`:

| Option | Flag | Default | Description |
|--------|------|---------|-------------|
| Init codeplug | `--init-codeplug` | On | Reset radio to factory defaults before writing. Recommended — prevents stale settings from prior codeplugs |
| Sync device clock | `--update-device-clock` | Off | Set the radio's clock to current system time during write |
| Auto-enable GPS | `--auto-enable-gps` | Off | Enable GPS hardware on radios that support it |
| Auto-enable roaming | `--auto-enable-roaming` | Off | Enable roaming on radios that support it |

Switch states are persisted to `~/.config/plugsmith/config.toml` on every toggle.

### The [0%] Quirk

dmrconf always shows `[0%]` at the start of a write, then exits with
"Upload completed". This is **normal and correct** — it is not stalled.
The `[0%]` is a display artifact in dmrconf's progress reporting.

Exit code 0 = success. Do **not** run write a second time.

### If Write Fails

1. Power-cycle the radio (turn off, turn on)
2. Reconnect USB
3. Retry the write immediately after the radio boots
4. If it fails again, try Read first to confirm the radio is communicating

## Format Conversion (offline)

The **Format Conversion** collapsible lets you convert between YAML and DFU formats
without a connected radio.

**Encode .yaml → .dfu** — convert codeplug.yaml to a binary DFU file:
```
backups/878uvii_20260303_104200.dfu
```

**Decode .dfu → .yaml** — convert a DFU binary back to human-readable YAML.
Enter the source `.dfu` path in the "Source .dfu:" field first.

Output is saved to the backup directory with an auto-generated timestamp name.

## Callsign Database

The **Callsign Database** collapsible writes a DMR ID → callsign lookup database
to your radio's memory (used for over-the-air ID decoding).

| Field | Description |
|-------|-------------|
| DMR ID | Your DMR ID. Auto-populated from codeplug config.yaml if left blank |
| DB JSON path | Path to a pre-downloaded callsign DB JSON. Leave blank to download from BrandMeister |
| Max entries | Limit how many entries to write (`--limit N`). Leave blank for no limit |

**Write DB to Radio** — downloads and writes the callsign DB to the connected radio.

**Encode DB to File** — encodes the callsign DB to a JSON file in the backup directory,
without touching the radio. Useful for offline inspection or manual transfer.

## Backup Naming Convention

```
backups/878uvii_YYYYMMDD_HHMMSS.dfu      # binary — use to restore
backups/878uvii_YYYYMMDD_HHMMSS.yaml     # human-readable — use to inspect
backups/878uvii_YYYYMMDD_HHMMSS.csv      # Anytone CPS CSV
backups/878uvii_YYYYMMDD_HHMMSS_db.json  # encoded callsign DB
```

Keep at least one recent .dfu backup before every write.
