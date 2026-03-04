"""Locate and verify the dmrconf binary."""

from __future__ import annotations

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


def builder_version() -> str:
    """Return the bundled builder version string."""
    return f"bundled v{__version__}"
