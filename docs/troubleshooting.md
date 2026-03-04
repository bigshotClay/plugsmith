# Troubleshooting

## dmrconf not found

**Symptom:** StatusBar shows `dmrconf: NOT FOUND` in red.

**Fix:**
1. Install dmrconf — see [Installation](installation.md)
2. Make sure it is on your PATH: `which dmrconf`
3. If it's in a non-standard location, set it in plugsmith config:
   - Config tab → `dmrconf_path` field (or edit `~/.config/plugsmith/config.toml` directly)

---

## Setup wizard auto-detect finds no device

**Symptom:** "Start Detection" times out with "No device detected."

**Fixes:**
- Make sure you unplugged the radio *before* clicking Start Detection (the wizard
  watches for a new device to appear)
- Confirm the USB cable is plugged in and data-capable (not a charge-only cable)
- Try a different USB port
- If detection still fails, enter the device path manually:
  - macOS: `ls /dev/cu.usb*` to find the name, then paste it into the Device path field
  - Linux: `ls /dev/ttyUSB*` or `dmesg | tail -20` after plugging in
  - Linux: add yourself to the `dialout` group: `sudo usermod -aG dialout $USER` (then log out/in)
  - WSL: use usbipd-win to attach the device (see [Installation](installation.md))

---

## Device not found / detect fails (Radio tab)

**Symptom:** Detect fails with "device not found" or timeout.

**Fixes:**
- Confirm the USB cable is plugged in and data-capable (not a charge-only cable)
- On macOS: `ls /dev/cu.usb*` to find the device name
- On Linux: `ls /dev/ttyUSB*` or `dmesg | tail -20` after plugging in
- On Linux: add yourself to `dialout` group: `sudo usermod -aG dialout $USER`
- On WSL: use usbipd-win to attach the device (see [Installation](installation.md))
- Try a different USB port

---

## Build failed: 429 rate limit

**Symptom:** Build log shows `429 — waiting 90s`.

**Explanation:** RepeaterBook rate-limits API clients after many rapid requests.
plugsmith automatically waits 90 seconds and retries.

**What to do:** Wait — the build will continue automatically.

**To avoid in the future:**
- Increase `rate_limit_seconds` in config.yaml (default 2.0 — do not lower it)
- RepeaterBook cache stays valid for 30 days; subsequent builds skip cached states entirely

---

## Build failed: 401 Unauthorized

**Symptom:** Build log shows `401` when fetching a state.

**Fix:** RepeaterBook requires a valid email in the HTTP User-Agent.
plugsmith uses your callsign. If the problem persists, check that your
config.yaml has a valid `callsign` set.

---

## Radio not responding after write

**Symptom:** Radio shows unusual display or write times out.

**Recovery:**
1. Power-cycle the radio (remove battery if needed)
2. Reconnect USB
3. Try Read to confirm communication
4. Retry write once
5. If still failing, use your .dfu backup: `dmrconf write --radio d878uv2 --device <device> --init-codeplug backup.dfu`

---

## The app crashes on launch

**Symptom:** `plugsmith` exits immediately with a Python traceback.

**Fix:**
1. Check Python version: `python3 --version` (must be 3.11+)
2. Reinstall: `pip install --upgrade plugsmith`
3. Check for a corrupt config: `rm ~/.config/plugsmith/config.toml` (re-runs wizard)
4. [Open an issue](https://github.com/bigshotClay/plugsmith/issues) with the full traceback

---

## Where to find logs

plugsmith writes to stdout — run from a terminal to see all output.
The output log in the Build and Radio tabs captures per-operation output.

---

## Getting more help

- [GitHub Issues](https://github.com/bigshotClay/plugsmith/issues) — bug reports
- [Docs](https://github.com/bigshotClay/plugsmith/tree/main/docs) — full documentation
