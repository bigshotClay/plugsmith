"""Reusable labeled form row widgets."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widget import Widget
from textual.widgets import Input, Label, Switch


class LabeledInput(Widget):
    """Horizontal row: fixed-width Label + Input."""

    DEFAULT_CSS = """
    LabeledInput {
        height: 3;
        margin: 0 0 1 0;
    }
    LabeledInput Horizontal {
        height: 3;
        align: left middle;
    }
    LabeledInput Label {
        width: 24;
        padding: 1 1 1 0;
        text-align: right;
        color: $text-muted;
    }
    LabeledInput Input {
        width: 1fr;
    }
    """

    def __init__(
        self,
        label: str,
        input_id: str,
        placeholder: str = "",
        value: str = "",
        password: bool = False,
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)
        self._label = label
        self._input_id = input_id
        self._placeholder = placeholder
        self._value = value
        self._password = password

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Label(self._label)
            yield Input(
                value=self._value,
                placeholder=self._placeholder,
                password=self._password,
                id=self._input_id,
            )

    @property
    def value(self) -> str:
        return self.query_one(f"#{self._input_id}", Input).value

    @value.setter
    def value(self, val: str) -> None:
        self.query_one(f"#{self._input_id}", Input).value = val


class LabeledSwitch(Widget):
    """Horizontal row: fixed-width Label + Switch."""

    DEFAULT_CSS = """
    LabeledSwitch {
        height: 3;
        margin: 0 0 1 0;
    }
    LabeledSwitch Horizontal {
        height: 3;
        align: left middle;
    }
    LabeledSwitch Label {
        width: 24;
        padding: 1 1 1 0;
        text-align: right;
        color: $text-muted;
    }
    """

    def __init__(
        self,
        label: str,
        switch_id: str,
        value: bool = False,
        **kwargs: object,
    ) -> None:
        super().__init__(id=switch_id, **kwargs)
        self._label = label
        self._value = value

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Label(self._label)
            yield Switch(value=self._value)

    @property
    def value(self) -> bool:
        return self.query_one(Switch).value

    @value.setter
    def value(self, val: bool) -> None:
        self.query_one(Switch).value = val
