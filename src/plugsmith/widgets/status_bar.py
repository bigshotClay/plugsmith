"""Persistent status bar showing tool health and radio connection."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Label
from textual.containers import Horizontal

from plugsmith.tool_discovery import find_dmrconf, builder_version


class StatusBar(Widget):
    """Persistent row: dmrconf health | builder | config | radio connection."""

    DEFAULT_CSS = """
    StatusBar {
        height: 1;
        background: $panel-darken-1;
        padding: 0 1;
    }
    StatusBar Horizontal {
        height: 1;
    }
    StatusBar Label {
        margin: 0 1;
        height: 1;
    }
    StatusBar .sep {
        color: $text-muted;
    }
    StatusBar .ok {
        color: $success;
    }
    StatusBar .warn {
        color: $warning;
    }
    StatusBar .error {
        color: $error;
    }
    """

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Label("dmrconf: checking…", id="lbl-dmrconf")
            yield Label("|", classes="sep")
            yield Label(f"builder: {builder_version()}", id="lbl-builder", classes="ok")
            yield Label("|", classes="sep")
            yield Label("config: not set", id="lbl-config")
            yield Label("|", classes="sep")
            yield Label("radio: ● not connected", id="lbl-radio", classes="warn")

    def on_mount(self) -> None:
        self.refresh_dmrconf()

    def refresh_dmrconf(self, path: str = "") -> None:
        status = find_dmrconf(path)
        lbl = self.query_one("#lbl-dmrconf", Label)
        if status.found:
            lbl.update(f"dmrconf: {status.version or 'ok'}")
            lbl.set_class(True, "ok")
            lbl.set_class(False, "error")
        else:
            lbl.update("dmrconf: [red]NOT FOUND[/red]")
            lbl.set_class(False, "ok")
            lbl.set_class(True, "error")

    def set_config_path(self, path: str) -> None:
        lbl = self.query_one("#lbl-config", Label)
        if path:
            import os
            lbl.update(f"config: {os.path.basename(path)}")
            lbl.set_class(True, "ok")
            lbl.set_class(False, "warn")
        else:
            lbl.update("config: not set")
            lbl.set_class(False, "ok")
            lbl.set_class(True, "warn")

    def set_radio_status(self, connected: bool, detail: str = "") -> None:
        lbl = self.query_one("#lbl-radio", Label)
        if connected:
            lbl.update(f"radio: [green]● connected[/green]{' — ' + detail if detail else ''}")
            lbl.set_class(True, "ok")
            lbl.set_class(False, "warn")
        else:
            lbl.update("radio: ● not connected")
            lbl.set_class(False, "ok")
            lbl.set_class(True, "warn")
