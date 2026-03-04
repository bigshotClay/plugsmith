"""Tests for generic_hw_settings helper functions."""

import pytest

from plugsmith.screens.generic_hw_settings import (
    _flatten,
    _infer_type,
    _sanitize_id,
    _unflatten,
    camel_to_title,
)


# ---------------------------------------------------------------------------
# camel_to_title
# ---------------------------------------------------------------------------

def test_camel_to_title_basic():
    assert camel_to_title("bootDisplay") == "Boot Display"


def test_camel_to_title_multi_word():
    assert camel_to_title("funcKey1Short") == "Func Key 1 Short"


def test_camel_to_title_long():
    assert camel_to_title("powerSaveSettings") == "Power Save Settings"


def test_camel_to_title_snake_case():
    assert camel_to_title("snake_case_key") == "Snake Case Key"


def test_camel_to_title_single_word():
    assert camel_to_title("volume") == "Volume"


def test_camel_to_title_already_title():
    assert camel_to_title("MicGain") == "Mic Gain"


# ---------------------------------------------------------------------------
# _sanitize_id
# ---------------------------------------------------------------------------

def test_sanitize_id_dots():
    assert _sanitize_id("bootSettings.bootDisplay") == "bootSettings-bootDisplay"


def test_sanitize_id_spaces():
    assert _sanitize_id("key with spaces") == "key-with-spaces"


def test_sanitize_id_alphanumeric_unchanged():
    assert _sanitize_id("simpleKey") == "simpleKey"


def test_sanitize_id_nested():
    assert _sanitize_id("a.b.c") == "a-b-c"


# ---------------------------------------------------------------------------
# _infer_type
# ---------------------------------------------------------------------------

def test_infer_type_bool_true():
    assert _infer_type(True) == "bool"


def test_infer_type_bool_false():
    assert _infer_type(False) == "bool"


def test_infer_type_int():
    assert _infer_type(5) == "int"


def test_infer_type_float():
    assert _infer_type(3.14) == "float"


def test_infer_type_str():
    assert _infer_type("Auto") == "str"


def test_infer_type_none():
    assert _infer_type(None) == "str"


def test_infer_type_dict():
    assert _infer_type({"nested": 1}) == "dict"


# ---------------------------------------------------------------------------
# _flatten
# ---------------------------------------------------------------------------

def test_flatten_nested():
    data = {"bootSettings": {"bootDisplay": "Default", "gpsCheck": False}, "micGain": 3}
    flat = _flatten(data)
    assert flat == {
        "bootSettings.bootDisplay": "Default",
        "bootSettings.gpsCheck": False,
        "micGain": 3,
    }


def test_flatten_flat_dict():
    data = {"a": 1, "b": 2}
    assert _flatten(data) == {"a": 1, "b": 2}


def test_flatten_deeply_nested():
    data = {"a": {"b": {"c": 42}}}
    assert _flatten(data) == {"a.b.c": 42}


def test_flatten_empty():
    assert _flatten({}) == {}


# ---------------------------------------------------------------------------
# _unflatten
# ---------------------------------------------------------------------------

def test_unflatten_simple():
    assert _unflatten({"a.b.c": 1}) == {"a": {"b": {"c": 1}}}


def test_unflatten_flat():
    assert _unflatten({"x": 10, "y": 20}) == {"x": 10, "y": 20}


def test_unflatten_empty():
    assert _unflatten({}) == {}


# ---------------------------------------------------------------------------
# round-trip: _flatten → _unflatten
# ---------------------------------------------------------------------------

def test_flatten_unflatten_round_trip():
    data = {"bootSettings": {"bootDisplay": "Default", "gpsCheck": False}, "micGain": 3}
    assert _unflatten(_flatten(data)) == data


def test_flatten_unflatten_nested():
    data = {"a": {"b": {"c": 1}}, "d": 2}
    assert _unflatten(_flatten(data)) == data
