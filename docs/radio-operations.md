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

Backups are auto-named with a timestamp. Location defaults to `backups/`
relative to your config.yaml.

## Verify

Click **Verify** to compare codeplug.yaml against the radio's current contents
without writing. Useful to confirm a write succeeded.

## Write to Radio

> **Warning: the write operation reboots the radio. Do not disconnect USB
> or repeat the write command while the radio is rebooting.**

1. Click **⚠ Write to Radio**
2. Read the confirmation dialog carefully
3. Click **Confirm**
4. Watch the output log — you will see `[0%]` then `Upload completed`
5. The radio reboots immediately. Wait ~10 seconds before disconnecting.

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

## Backup Naming Convention

```
backups/878uvii_YYYYMMDD_HHMMSS.dfu    # binary — use to restore
backups/878uvii_YYYYMMDD_HHMMSS.yaml   # human-readable — use to inspect
```

Keep at least one recent .dfu backup before every write.
