"""RichLog wrapper with Clear button and auto-scroll toggle."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.widgets import Button, RichLog, Switch
from textual.containers import Horizontal
from textual.widget import Widget
from textual import on


class OutputLog(Widget):
    """A scrollable output log with Clear and Auto-scroll controls."""

    DEFAULT_CSS = """
    OutputLog {
        height: 1fr;
    }
    OutputLog .log-toolbar {
        height: 1;
        background: $panel;
        padding: 0 1;
    }
    OutputLog .log-toolbar Button {
        height: 1;
        min-width: 7;
        border: none;
        background: $primary-darken-2;
    }
    OutputLog .log-toolbar Label {
        margin: 0 1;
        color: $text-muted;
    }
    """

    def compose(self) -> ComposeResult:
        with Horizontal(classes="log-toolbar"):
            yield Button("Clear", id="btn-clear-log", variant="default")
            from textual.widgets import Label
            yield Label("Auto-scroll:")
            yield Switch(value=True, id="switch-autoscroll")
        yield RichLog(id="rich-log", max_lines=5000, markup=True, wrap=False)

    def write_line(self, line: str, style: str | None = None) -> None:
        """Append a line to the log, optionally styled."""
        log = self.query_one("#rich-log", RichLog)
        if style:
            log.write(f"[{style}]{line}[/{style}]")
        else:
            log.write(line)
        if self._autoscroll:
            log.scroll_end(animate=False)

    def clear(self) -> None:
        self.query_one("#rich-log", RichLog).clear()

    @property
    def _autoscroll(self) -> bool:
        try:
            return self.query_one("#switch-autoscroll", Switch).value
        except Exception:
            return True

    @on(Button.Pressed, "#btn-clear-log")
    def _on_clear(self) -> None:
        self.clear()
