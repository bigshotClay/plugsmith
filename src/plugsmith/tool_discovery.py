"""Locate and verify the dmrconf binary."""

from __future__ import annotations

import platform
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from plugsmith import __version__


@dataclass
class ToolStatus:
    found: bool
    path: Optional[Path]
    version: Optional[str]
    error: Optional[str]


@dataclass
class RadioProfile:
    key: str                        # dmrconf model key, e.g. "d878uv2"
    display_name: str               # human name
    max_channels: int               # total channel capacity
    max_zones: int                  # total zone capacity
    max_channels_per_zone: int      # channels per zone
    hw_family: str                  # "anytone" | "tyt" | "radioddity" | "generic"
    hw_settings_key: Optional[str]  # config.yaml key for hw block, e.g. "anytone_settings"
    supported_modes: frozenset      # frozenset of mode strings this radio can physically do


_FM_DMR = frozenset({"fm", "dmr"})
_FM_DMR_FUSION = frozenset({"fm", "dmr", "fusion"})
_FM_DSTAR = frozenset({"fm", "dstar"})

RADIO_PROFILES: dict[str, RadioProfile] = {
    # AnyTone — FM + DMR only
    "d878uv2":  RadioProfile("d878uv2",  "AT-D878UVII (AnyTone)", 4000, 250, 160, "anytone",    "anytone_settings", _FM_DMR),
    "d878uv":   RadioProfile("d878uv",   "AT-D878UV (AnyTone)",   4000, 250, 160, "anytone",    "anytone_settings", _FM_DMR),
    "d868uv":   RadioProfile("d868uv",   "AT-D868UV (AnyTone)",   4000, 250, 160, "anytone",    "anytone_settings", _FM_DMR),
    "d578uv":   RadioProfile("d578uv",   "AT-D578UV (AnyTone)",   3000, 250, 160, "anytone",    "anytone_settings", _FM_DMR),
    # TYT — FM + DMR
    "uv390":    RadioProfile("uv390",    "MD-UV390 (TYT)",         3000, 250, 160, "tyt",        None, _FM_DMR),
    "md380":    RadioProfile("md380",    "MD-380 (TYT)",           1000, 250, 160, "tyt",        None, _FM_DMR),
    "md9600":   RadioProfile("md9600",   "MD-9600 (TYT)",          3000, 250, 160, "tyt",        None, _FM_DMR),
    # Radioddity — FM + DMR
    "gd77":     RadioProfile("gd77",     "GD-77 (Radioddity)",     1024, 250,  80, "radioddity", None, _FM_DMR),
    "gd77s":    RadioProfile("gd77s",    "GD-77S (Radioddity)",    1024, 250,  80, "radioddity", None, _FM_DMR),
    # Generic / Baofeng / Alinco — FM + DMR
    "d52uv":    RadioProfile("d52uv",    "RD-5R (Baofeng)",        1024, 250,  16, "generic",    None, _FM_DMR),
    "dr1801uv": RadioProfile("dr1801uv", "DR-1801UV (Alinco)",     1000, 250, 160, "generic",    None, _FM_DMR),
    # Yaesu — FM + DMR + Fusion (C4FM)
    "ft3d":     RadioProfile("ft3d",     "FT3D (Yaesu)",           900,  100, 100, "yaesu",      None, _FM_DMR_FUSION),
    "ft5d":     RadioProfile("ft5d",     "FT5D (Yaesu)",           900,  100, 100, "yaesu",      None, _FM_DMR_FUSION),
    # Icom — FM + D-Star
    "id51":     RadioProfile("id51",     "ID-51 (Icom)",           1000, 100, 100, "icom",       None, _FM_DSTAR),
    "id52":     RadioProfile("id52",     "ID-52 (Icom)",           1000, 100, 100, "icom",       None, _FM_DSTAR),
}

DEFAULT_RADIO_PROFILE = RadioProfile(
    "generic", "Generic DMR Radio", 4000, 250, 160, "generic", None, _FM_DMR
)


# Fallback list of common radio models when dmrconf --list-radios fails
_FALLBACK_RADIO_MODELS: list[tuple[str, str]] = [
    ("d878uv2",  "AT-D878UVII (AnyTone)"),
    ("d878uv",   "AT-D878UV (AnyTone)"),
    ("d868uv",   "AT-D868UV (AnyTone)"),
    ("d578uv",   "AT-D578UV (AnyTone)"),
    ("uv390",    "MD-UV390 (TYT)"),
    ("md380",    "MD-380 (TYT)"),
    ("md390",    "MD-390 (TYT)"),
    ("gd77",     "GD-77 (Radioddity)"),
    ("gd73",     "GD-73 (Radioddity)"),
    ("opengd77", "OpenGD77 (Radioddity)"),
    ("dm1801",   "DM-1801 (Baofeng)"),
    ("uv380",    "UV-380 (Baofeng)"),
]


def find_dmrconf(explicit_path: str = "") -> ToolStatus:
    """Locate and version-check the dmrconf binary.

    Args:
        explicit_path: If set, use this path instead of PATH search.
    """
    if explicit_path:
        candidate = Path(explicit_path).expanduser()
        if not candidate.exists():
            return ToolStatus(found=False, path=None, version=None,
                              error=f"dmrconf not found at configured path: {explicit_path}")
        path = candidate
    else:
        which = shutil.which("dmrconf")
        if not which:
            return ToolStatus(found=False, path=None, version=None,
                              error="dmrconf not found on PATH. Install from https://dm3mat.darc.de/qdmr/")
        path = Path(which)

    try:
        result = subprocess.run(
            [str(path), "--version"],
            capture_output=True, text=True, timeout=5,
        )
        version_line = (result.stdout or result.stderr or "").strip().splitlines()
        version = version_line[0] if version_line else "unknown"
        return ToolStatus(found=True, path=path, version=version, error=None)
    except (subprocess.SubprocessError, OSError) as e:
        return ToolStatus(found=False, path=path, version=None, error=str(e))


def list_radio_models(dmrconf_path: str = "") -> list[tuple[str, str]]:
    """Return list of (key, display_name) radio model tuples.

    Tries dmrconf --list-radios; falls back to a built-in list.
    """
    binary = dmrconf_path or shutil.which("dmrconf") or "dmrconf"
    try:
        result = subprocess.run(
            [binary, "--list-radios"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            models: list[tuple[str, str]] = []
            for line in result.stdout.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split(None, 1)
                if len(parts) == 2:
                    models.append((parts[0], parts[1]))
                elif len(parts) == 1:
                    models.append((parts[0], parts[0]))
            if models:
                return models
    except (subprocess.SubprocessError, OSError, FileNotFoundError):
        pass
    return _FALLBACK_RADIO_MODELS


def list_serial_devices() -> list[str]:
    """Return bare device names for connected serial/USB devices.

    Returns names without the /dev/ prefix to match the convention used
    throughout plugsmith (e.g. "cu.usbmodem0000000100001").

    macOS: /dev/cu.usb*
    Linux: /dev/ttyUSB* and /dev/ttyACM*
    """
    if platform.system() == "Darwin":
        patterns = ["/dev/cu.usb*"]
    else:
        patterns = ["/dev/ttyUSB*", "/dev/ttyACM*"]

    devices: list[str] = []
    for pattern in patterns:
        devices.extend(p.name for p in sorted(Path("/dev").glob(pattern.replace("/dev/", ""))))
    return devices


def detect_radio_model(device: str, dmrconf_path: str = "") -> str | None:
    """Run dmrconf detect against a device and return the matching RADIO_PROFILES key.

    Args:
        device: Bare device name (no /dev/ prefix), e.g. "cu.usbmodem0000000100001".
        dmrconf_path: Optional explicit path to dmrconf binary.

    Returns:
        A key from RADIO_PROFILES (e.g. "d878uv2") if the radio is recognised,
        or None if detection fails or the radio is unknown.
    """
    binary = dmrconf_path or shutil.which("dmrconf") or "dmrconf"
    try:
        result = subprocess.run(
            [binary, "detect", "--device", device],
            capture_output=True, text=True, timeout=10,
        )
        output = (result.stdout + result.stderr).lower()
    except (subprocess.SubprocessError, OSError, FileNotFoundError):
        return None

    # Match against RADIO_PROFILES keys using word boundaries so that "d878uv"
    # does not match inside "d878uvii".  Check longest keys first so more-specific
    # profiles (e.g. "d878uv2") are preferred over shorter prefixes ("d878uv").
    for key in sorted(RADIO_PROFILES, key=len, reverse=True):
        if re.search(rf"\b{re.escape(key)}\b", output):
            return key
    # Fall back to display name match (strip parenthetical brand suffix).
    for key, profile in sorted(
        RADIO_PROFILES.items(),
        key=lambda kv: len(kv[1].display_name),
        reverse=True,
    ):
        base_name = profile.display_name.split("(")[0].strip().lower()
        if base_name and base_name in output:
            return key
    return None


def builder_version() -> str:
    """Return the bundled builder version string."""
    return f"bundled v{__version__}"
