# Installation

## Requirements

- Python 3.11 or newer
- `dmrconf` installed (see below)
- A USB cable and compatible DMR radio

## Install plugsmith

```bash
pip install plugsmith
```

Verify the install:

```bash
plugsmith --version
```

## Install dmrconf

dmrconf is a separate C++ tool — plugsmith wraps it but does not bundle it.

**macOS (Homebrew):**
```bash
brew install qdmr
```

**Linux (Debian/Ubuntu):**
```bash
# Check https://dm3mat.darc.de/qdmr/ for the current deb package
wget https://dm3mat.darc.de/qdmr/files/qdmr_0.12.0-1_amd64.deb
sudo dpkg -i qdmr_0.12.0-1_amd64.deb
```

**Build from source:**
```bash
git clone https://github.com/DM3MAT/qdmr
cd qdmr && mkdir build && cd build
cmake .. && make
sudo make install
```

Verify:
```bash
dmrconf --version
```

## Platform Notes

### macOS

Device path format: `cu.usbmodem0000000100001` (no `/dev/` prefix in dmrconf)

```bash
ls /dev/cu.usb*   # find your device
```

### Linux

Device path format: `/dev/ttyUSB0` or `/dev/ttyACM0`

You may need to add yourself to the `dialout` group:
```bash
sudo usermod -aG dialout $USER
# log out and back in
```

### Windows (WSL2)

1. Install [usbipd-win](https://github.com/dorssel/usbipd-win) to share USB to WSL
2. In PowerShell (admin): `usbipd bind --busid <busid>` then `usbipd attach --wsl --busid <busid>`
3. Device appears as `/dev/ttyUSB0` or similar in WSL
4. Install plugsmith and dmrconf inside WSL

## Development Install

```bash
git clone https://github.com/bigshotClay/plugsmith
cd plugsmith
pip install -e ".[dev]"
```
