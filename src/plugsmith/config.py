"""plugsmith app-level configuration (separate from the user's codeplug config.yaml)."""

from __future__ import annotations

import tomllib
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

import tomli_w
from platformdirs import user_config_path

CONFIG_DIR = user_config_path("plugsmith")
CONFIG_FILE = CONFIG_DIR / "config.toml"


@dataclass
class PlugsmithConfig:
    """plugsmith's own settings — stored at ~/.config/plugsmith/config.toml."""

    dmrconf_path: str = ""        # empty = auto-detect via PATH
    codeplug_config: str = ""     # path to user's codeplug config.yaml
    codeplug_yaml: str = ""       # path to output codeplug.yaml
    device: str = ""              # e.g. cu.usbmodem0000000100001
    radio_model: str = ""         # e.g. d878uv2
    backup_dir: str = "backups"   # relative to codeplug_config dir, or absolute
    init_codeplug: bool = True    # pass --init-codeplug on write
    last_tab: str = "tab-dashboard"
    hw_submitted_firmware: str = ""  # firmware version recorded at last hw config submission

    def is_complete(self) -> bool:
        """True when enough settings are present to run without the setup wizard."""
        return bool(self.codeplug_config and self.device and self.radio_model)

    def save(self) -> None:
        """Persist to ~/.config/plugsmith/config.toml."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data = asdict(self)
        with open(CONFIG_FILE, "wb") as f:
            tomli_w.dump(data, f)

    @property
    def codeplug_config_path(self) -> Optional[Path]:
        """Resolved Path to the codeplug config.yaml, or None."""
        if self.codeplug_config:
            return Path(self.codeplug_config).expanduser()
        return None

    @property
    def codeplug_yaml_path(self) -> Path:
        """Resolved output YAML path. Falls back to codeplug.yaml next to config."""
        if self.codeplug_yaml:
            return Path(self.codeplug_yaml).expanduser()
        if self.codeplug_config:
            return Path(self.codeplug_config).parent / "codeplug.yaml"
        return Path("codeplug.yaml")

    @property
    def backup_dir_path(self) -> Path:
        """Resolved backup directory path."""
        bd = Path(self.backup_dir)
        if bd.is_absolute():
            return bd
        if self.codeplug_config:
            return Path(self.codeplug_config).parent / bd
        return bd


def load_app_config() -> PlugsmithConfig:
    """Load plugsmith config from disk, returning defaults if missing."""
    if not CONFIG_FILE.exists():
        return PlugsmithConfig()
    try:
        with open(CONFIG_FILE, "rb") as f:
            data = tomllib.load(f)
        return PlugsmithConfig(**{k: v for k, v in data.items() if k in PlugsmithConfig.__dataclass_fields__})
    except Exception:
        return PlugsmithConfig()
