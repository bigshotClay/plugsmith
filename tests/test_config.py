"""Tests for plugsmith.config."""

import tomllib
from pathlib import Path

import pytest

from plugsmith.config import PlugsmithConfig, load_app_config


def test_is_complete_false_by_default():
    cfg = PlugsmithConfig()
    assert not cfg.is_complete()


def test_is_complete_true_when_all_set():
    cfg = PlugsmithConfig(
        codeplug_config="/tmp/config.yaml",
        device="cu.usbmodem0000000100001",
        radio_model="d878uv2",
    )
    assert cfg.is_complete()


def test_save_and_reload(tmp_path, monkeypatch):
    """Save a config and reload it."""
    monkeypatch.setattr("plugsmith.config.CONFIG_DIR", tmp_path)
    monkeypatch.setattr("plugsmith.config.CONFIG_FILE", tmp_path / "config.toml")

    cfg = PlugsmithConfig(
        codeplug_config="/tmp/config.yaml",
        device="cu.usbmodem",
        radio_model="d878uv2",
    )
    cfg.save()

    loaded = load_app_config()
    assert loaded.codeplug_config == "/tmp/config.yaml"
    assert loaded.device == "cu.usbmodem"
    assert loaded.radio_model == "d878uv2"


def test_codeplug_yaml_path_fallback():
    cfg = PlugsmithConfig(codeplug_config="/home/user/ham/config.yaml")
    assert cfg.codeplug_yaml_path == Path("/home/user/ham/codeplug.yaml")


def test_codeplug_yaml_path_explicit():
    cfg = PlugsmithConfig(
        codeplug_config="/home/user/ham/config.yaml",
        codeplug_yaml="/home/user/ham/my.yaml",
    )
    assert cfg.codeplug_yaml_path == Path("/home/user/ham/my.yaml")


# ---------------------------------------------------------------------------
# New write-option fields (added in 0.4.0)
# ---------------------------------------------------------------------------


def test_new_fields_have_correct_defaults():
    cfg = PlugsmithConfig()
    assert cfg.update_device_clock is False
    assert cfg.auto_enable_gps is False
    assert cfg.auto_enable_roaming is False
    assert cfg.callsign_db_path == ""
    assert cfg.callsign_limit == 0


def test_new_fields_persist_through_save_reload(tmp_path, monkeypatch):
    monkeypatch.setattr("plugsmith.config.CONFIG_DIR", tmp_path)
    monkeypatch.setattr("plugsmith.config.CONFIG_FILE", tmp_path / "config.toml")

    cfg = PlugsmithConfig(
        update_device_clock=True,
        auto_enable_gps=True,
        auto_enable_roaming=True,
        callsign_db_path="/tmp/db.json",
        callsign_limit=1000,
    )
    cfg.save()

    loaded = load_app_config()
    assert loaded.update_device_clock is True
    assert loaded.auto_enable_gps is True
    assert loaded.auto_enable_roaming is True
    assert loaded.callsign_db_path == "/tmp/db.json"
    assert loaded.callsign_limit == 1000


def test_init_codeplug_defaults_true():
    cfg = PlugsmithConfig()
    assert cfg.init_codeplug is True


def test_init_codeplug_persists_false(tmp_path, monkeypatch):
    monkeypatch.setattr("plugsmith.config.CONFIG_DIR", tmp_path)
    monkeypatch.setattr("plugsmith.config.CONFIG_FILE", tmp_path / "config.toml")

    cfg = PlugsmithConfig(init_codeplug=False)
    cfg.save()
    loaded = load_app_config()
    assert loaded.init_codeplug is False


def test_callsign_limit_zero_is_default():
    """Zero means 'omit --limit flag' — ensure it round-trips cleanly."""
    cfg = PlugsmithConfig(callsign_limit=0)
    assert cfg.callsign_limit == 0


def test_backup_dir_path_absolute():
    cfg = PlugsmithConfig(backup_dir="/absolute/backups")
    assert cfg.backup_dir_path == Path("/absolute/backups")


def test_backup_dir_path_relative_to_config():
    cfg = PlugsmithConfig(
        codeplug_config="/home/user/ham/config.yaml",
        backup_dir="backups",
    )
    assert cfg.backup_dir_path == Path("/home/user/ham/backups")


def test_backup_dir_path_relative_no_config():
    """Relative backup_dir with no codeplug_config returns bare relative path."""
    cfg = PlugsmithConfig(backup_dir="backups")
    assert cfg.backup_dir_path == Path("backups")


# ---------------------------------------------------------------------------
# codeplug_config_path property
# ---------------------------------------------------------------------------


def test_codeplug_config_path_returns_none_when_unset():
    cfg = PlugsmithConfig()
    assert cfg.codeplug_config_path is None


def test_codeplug_config_path_returns_path_when_set():
    cfg = PlugsmithConfig(codeplug_config="/home/user/ham/config.yaml")
    assert cfg.codeplug_config_path == Path("/home/user/ham/config.yaml")


# ---------------------------------------------------------------------------
# codeplug_yaml_path fallback when neither is set
# ---------------------------------------------------------------------------


def test_codeplug_yaml_path_bare_fallback():
    """When neither codeplug_yaml nor codeplug_config is set, returns bare codeplug.yaml."""
    cfg = PlugsmithConfig()
    assert cfg.codeplug_yaml_path == Path("codeplug.yaml")


# ---------------------------------------------------------------------------
# load_app_config edge cases
# ---------------------------------------------------------------------------


def test_load_app_config_returns_defaults_when_file_missing(tmp_path, monkeypatch):
    """load_app_config returns default PlugsmithConfig when config file doesn't exist."""
    monkeypatch.setattr("plugsmith.config.CONFIG_FILE", tmp_path / "nonexistent.toml")
    cfg = load_app_config()
    assert isinstance(cfg, PlugsmithConfig)
    assert cfg.device == ""
    assert cfg.radio_model == ""


def test_load_app_config_returns_defaults_on_corrupt_file(tmp_path, monkeypatch):
    """load_app_config returns default PlugsmithConfig when file is corrupt."""
    cfg_file = tmp_path / "corrupt.toml"
    cfg_file.write_bytes(b"\xff\xfe invalid toml content %%@@")
    monkeypatch.setattr("plugsmith.config.CONFIG_FILE", cfg_file)
    cfg = load_app_config()
    assert isinstance(cfg, PlugsmithConfig)
    assert cfg.device == ""
