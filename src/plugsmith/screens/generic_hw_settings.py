"""GenericHwPane — auto-generates a hardware settings form from an arbitrary dict.

Used for non-AnyTone radios where no rich SettingMeta metadata exists.
Types are inferred from the existing values in config.yaml.
"""

from __future__ import annotations

import re
from typing import Any

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widget import Widget
from textual.widgets import Collapsible, Input, Label, Switch


# ---------------------------------------------------------------------------
# Pure helper functions (tested without Textual)
# ---------------------------------------------------------------------------

def camel_to_title(key: str) -> str:
    """Convert a camelCase or snake_case key to a Title Case display name.

    Examples:
        "bootDisplay"      → "Boot Display"
        "funcKey1Short"    → "Func Key 1 Short"
        "powerSaveSettings" → "Power Save Settings"
        "snake_case_key"   → "Snake Case Key"
    """
    # Insert space before uppercase letters
    s = re.sub(r'([A-Z])', r' \1', key)
    # Insert space between a lowercase letter and a digit (e.g. "Key1" → "Key 1")
    s = re.sub(r'([a-zA-Z])(\d)', r'\1 \2', s)
    # Insert space between a digit and an uppercase letter (e.g. "1Short" → "1 Short")
    s = re.sub(r'(\d)([A-Z])', r'\1 \2', s)
    # Replace underscores with spaces
    s = s.replace('_', ' ')
    return s.strip().title()


def _sanitize_id(path: str) -> str:
    """Convert a dotted path to a CSS-safe widget ID fragment.

    Example: "bootSettings.bootDisplay" → "bootSettings-bootDisplay"
    """
    return re.sub(r'[^a-zA-Z0-9_-]', '-', path)


def _infer_type(value: Any) -> str:
    """Infer a type tag from a Python value.

    Returns one of: 'bool', 'int', 'float', 'dict', 'str'.
    """
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, dict):
        return "dict"
    return "str"


def _flatten(data: dict, prefix: str = "") -> dict[str, Any]:
    """Flatten a nested dict to dotted-key leaf values.

    Example:
        {"bootSettings": {"bootDisplay": "Default", "gpsCheck": False}, "micGain": 3}
        → {"bootSettings.bootDisplay": "Default", "bootSettings.gpsCheck": False, "micGain": 3}
    """
    result: dict[str, Any] = {}
    for key, val in data.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(val, dict):
            result.update(_flatten(val, prefix=full_key))
        else:
            result[full_key] = val
    return result


def _unflatten(flat: dict[str, Any]) -> dict:
    """Rebuild a nested dict from dotted-key paths.

    Example:
        {"a.b.c": 1} → {"a": {"b": {"c": 1}}}
    """
    result: dict = {}
    for dotted_key, val in flat.items():
        parts = dotted_key.split(".")
        d = result
        for part in parts[:-1]:
            d = d.setdefault(part, {})
        d[parts[-1]] = val
    return result


# ---------------------------------------------------------------------------
# Textual widget
# ---------------------------------------------------------------------------

class GenericHwPane(Widget):
    """Auto-generates an editable form from an arbitrary settings dict.

    No descriptions, warnings, or ham-preferred labels — just type-inferred
    controls for each leaf value.

    Widget IDs follow the pattern: gen-{sanitized_dotted_path}
    e.g. "gen-bootSettings-bootDisplay"
    """

    DEFAULT_CSS = """
    GenericHwPane .gen-section {
        margin: 0 0 1 0;
    }
    GenericHwPane .gen-row {
        height: 3;
        align: left middle;
    }
    GenericHwPane .gen-label {
        width: 30;
        padding: 1 1 1 0;
        color: $text;
        text-style: bold;
    }
    GenericHwPane .gen-control {
        width: 1fr;
    }
    """

    def __init__(self, settings_key: str, data: dict, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._settings_key = settings_key
        self._data = data
        self._flat = _flatten(data)
        self._type_map: dict[str, str] = {k: _infer_type(v) for k, v in self._flat.items()}

    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        """Build form widgets from the settings dict structure."""
        for top_key, top_val in self._data.items():
            if isinstance(top_val, dict):
                with Collapsible(title=camel_to_title(top_key), collapsed=False, classes="gen-section"):
                    yield from self._compose_group(top_key, top_val)
            else:
                yield from self._compose_leaf(top_key, top_val)

    def _compose_group(self, prefix: str, group: dict) -> ComposeResult:
        """Recursively yield leaf widgets under a section prefix."""
        for key, val in group.items():
            dotted = f"{prefix}.{key}"
            if isinstance(val, dict):
                # Nested sub-group — render inline (no extra collapsible)
                yield from self._compose_group(dotted, val)
            else:
                yield from self._compose_leaf(dotted, val)

    def _compose_leaf(self, dotted_path: str, value: Any) -> ComposeResult:
        """Yield a single labeled control row for a leaf value."""
        # Use only the last segment for display
        label_text = camel_to_title(dotted_path.split(".")[-1])
        widget_id = f"gen-{_sanitize_id(dotted_path)}"
        inferred = _infer_type(value)
        with Horizontal(classes="gen-row"):
            yield Label(label_text, classes="gen-label")
            if inferred == "bool":
                yield Switch(value=bool(value), id=widget_id, classes="gen-control")
            else:
                yield Input(
                    value=str(value) if value is not None else "",
                    id=widget_id,
                    classes="gen-control",
                )

    # ------------------------------------------------------------------

    def collect(self) -> dict:
        """Read current widget values and return a reconstructed nested dict.

        Types are coerced back to original Python types using _type_map.
        """
        result_flat: dict[str, Any] = {}
        for dotted_path, original_val in self._flat.items():
            widget_id = f"gen-{_sanitize_id(dotted_path)}"
            inferred = self._type_map.get(dotted_path, "str")
            try:
                if inferred == "bool":
                    result_flat[dotted_path] = self.query_one(f"#{widget_id}", Switch).value
                else:
                    raw = self.query_one(f"#{widget_id}", Input).value
                    if inferred == "int":
                        try:
                            result_flat[dotted_path] = int(raw)
                        except (ValueError, TypeError):
                            result_flat[dotted_path] = original_val
                    elif inferred == "float":
                        try:
                            result_flat[dotted_path] = float(raw)
                        except (ValueError, TypeError):
                            result_flat[dotted_path] = original_val
                    else:
                        result_flat[dotted_path] = raw
            except Exception:
                result_flat[dotted_path] = original_val
        return _unflatten(result_flat)
