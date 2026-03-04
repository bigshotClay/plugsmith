# Quick Start

Get from zero to a programmed radio in under 10 minutes.

## Step 1: Install

```bash
pip install plugsmith
```

Make sure dmrconf is also installed. See [Installation](installation.md).

## Step 2: Launch

```bash
plugsmith
```

On first launch, the **Setup Wizard** appears automatically.

## Step 3: Setup Wizard

**Step 1 — Locate config.yaml:**
- If you have an existing config.yaml, click Browse and select it
- If not, click **Create New** — a starter config is created in `~/codeplug/config.yaml`

**Step 2 — Radio setup:**
- Enter your USB device path (e.g. `cu.usbmodem0000000100001` on macOS)
- Select your radio model from the dropdown

**Step 3 — Confirm:**
- Review settings, click **Save & Launch**

## Step 4: Edit your config (Config tab)

Go to the **Config** tab (`Ctrl+E`) and fill in:
- **DMR ID** — your 7-digit BrandMeister ID (register at radioid.net)
- **Callsign** — your amateur callsign
- **Latitude / Longitude** — your QTH (home location)
- **Home State** — your state abbreviation (e.g. MO)

Click **Save Config**.

## Step 5: Build your codeplug (Build tab)

Go to the **Build** tab (`Ctrl+B`):
1. Confirm the config.yaml path is set
2. Click **▶ Build Codeplug**
3. Watch the output — it will fetch all 50 states (cached after first run)
4. When complete: "✓ Done: 4000 channels, 71 zones"

> Tip: The first full build takes a few minutes (fetches 50 states from RepeaterBook).
> Subsequent builds are fast — cached data is reused for 12 hours.

## Step 6: Back up your radio (Radio tab)

Before writing, read the current codeplug:
1. Go to the **Radio** tab (`Ctrl+R`)
2. Click **Read .dfu** — creates a timestamped backup
3. Verify the backup file appears in the output log

## Step 7: Write to radio

1. Click **⚠ Write to Radio**
2. Read the confirmation dialog
3. Click **Confirm**
4. Watch for: `Upload completed` — that's success!
5. Wait ~10 seconds for the radio to reboot

Your radio is now programmed.

## Next steps

- Adjust config.yaml tiers and filters in the Config tab
- Rebuild after config changes
- See [Radio Operations](radio-operations.md) for write/read/verify details
- See [Configuration](configuration.md) for all config options
