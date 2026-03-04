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
