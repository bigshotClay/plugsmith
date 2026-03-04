"""MainScreen — root screen with TabbedContent and StatusBar."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual import on
from textual.widgets import Button, Footer, Header, Static, TabbedContent, TabPane

from plugsmith.widgets.status_bar import StatusBar
from plugsmith.screens.build_screen import BuildPane
from plugsmith.screens.radio_screen import RadioPane
from plugsmith.screens.config_editor import ConfigEditorPane
from plugsmith.screens.roaming_screen import RoamingPane


class DashboardPane(TabPane):
    """Dashboard tab — shows codeplug stats and quick launch buttons."""

    DEFAULT_CSS = """
    DashboardPane {
        padding: 1 2;
    }
    DashboardPane .stat-grid {
        height: auto;
        margin-bottom: 1;
    }
    DashboardPane .stat-row {
        height: 2;
    }
    DashboardPane .stat-label {
        width: 20;
        color: $text-muted;
    }
    DashboardPane .stat-value {
        color: $success;
        text-style: bold;
    }
    DashboardPane .quick-actions {
        height: 3;
        margin-top: 1;
    }
    DashboardPane .quick-actions Button {
        margin-right: 1;
    }
    #dash-hw-notice {
        display: none;
        margin-top: 1;
    }
    #dash-btn-hw-submit {
        display: none;
        margin-top: 1;
    }
    """

    def compose(self) -> ComposeResult:
        from textual.containers import Horizontal, Vertical
        from textual.widgets import Button, Label, Static

        with Vertical():
            yield Label("[bold]Codeplug Status[/bold]")
            with Vertical(classes="stat-grid"):
                with Horizontal(classes="stat-row"):
                    yield Label("Codeplug:", classes="stat-label")
                    yield Label("—", id="dash-codeplug-path", classes="stat-value")
                with Horizontal(classes="stat-row"):
                    yield Label("Channels:", classes="stat-label")
                    yield Label("—", id="dash-channels", classes="stat-value")
                with Horizontal(classes="stat-row"):
                    yield Label("Zones:", classes="stat-label")
                    yield Label("—", id="dash-zones", classes="stat-value")
                with Horizontal(classes="stat-row"):
                    yield Label("Last built:", classes="stat-label")
                    yield Label("—", id="dash-last-built", classes="stat-value")
                with Horizontal(classes="stat-row"):
                    yield Label("Config:", classes="stat-label")
                    yield Label("—", id="dash-config-path", classes="stat-value")
            with Horizontal(classes="quick-actions"):
                yield Button("▶ Build", id="dash-btn-build", variant="primary")
                yield Button("Write to Radio", id="dash-btn-radio", variant="warning")
                yield Button("Edit Config", id="dash-btn-config", variant="default")
            yield Static("", id="dash-hw-notice", markup=True)
            yield Button("Submit Hardware Config", id="dash-btn-hw-submit", variant="primary")

    def on_mount(self) -> None:
        self.refresh_stats()

    def refresh_stats(self) -> None:
        from plugsmith.config import load_app_config
        import os

        cfg = load_app_config()

        if cfg.codeplug_config:
            self.query_one("#dash-config-path").update(
                os.path.basename(cfg.codeplug_config)
            )

        yaml_path = cfg.codeplug_yaml_path
        if yaml_path.exists():
            self.query_one("#dash-codeplug-path").update(str(yaml_path))
            import time
            mtime = yaml_path.stat().st_mtime
            import datetime
            dt = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
            self.query_one("#dash-last-built").update(dt)
            try:
                import yaml
                from plugsmith.tool_discovery import RADIO_PROFILES, DEFAULT_RADIO_PROFILE
                profile = RADIO_PROFILES.get(cfg.radio_model, DEFAULT_RADIO_PROFILE)
                with open(yaml_path) as f:
                    cp = yaml.safe_load(f)
                if cp:
                    n_ch = len(cp.get("channels", []))
                    n_zones = len(cp.get("zones", []))
                    self.query_one("#dash-channels").update(f"{n_ch} / {profile.max_channels}")
                    self.query_one("#dash-zones").update(str(n_zones))
            except Exception:
                pass

        from plugsmith.hw_submit import is_submission_needed
        from plugsmith.tool_discovery import RADIO_PROFILES, DEFAULT_RADIO_PROFILE
        needs = is_submission_needed(cfg.radio_model, cfg.hw_submitted_firmware)
        self.query_one("#dash-hw-notice", Static).display = needs
        self.query_one("#dash-btn-hw-submit", Button).display = needs
        if needs:
            profile = RADIO_PROFILES.get(cfg.radio_model, DEFAULT_RADIO_PROFILE)
            self.query_one("#dash-hw-notice", Static).update(
                f"[yellow]⚠ {profile.display_name} is not fully supported yet. "
                "Submit your hardware config to help improve plugsmith.[/yellow]"
            )

    @on(Button.Pressed, "#dash-btn-hw-submit")
    def _open_hw_submit(self) -> None:
        from plugsmith.config import load_app_config
        cfg = load_app_config()
        hw_yaml = ""
        if cfg.codeplug_config_path and cfg.codeplug_config_path.exists():
            try:
                import yaml
                from plugsmith.builder.build_config import load_config
                raw = load_config(str(cfg.codeplug_config_path))
                from plugsmith.tool_discovery import RADIO_PROFILES, DEFAULT_RADIO_PROFILE
                profile = RADIO_PROFILES.get(cfg.radio_model, DEFAULT_RADIO_PROFILE)
                hw_key = profile.hw_settings_key or f"{cfg.radio_model}_settings"
                hw_block = raw.get(hw_key, {})
                hw_yaml = yaml.dump(hw_block) if hw_block else ""
            except Exception:
                pass
        from plugsmith.screens.hw_submit_modal import HardwareSubmitModal
        self.app.push_screen(
            HardwareSubmitModal(cfg.radio_model, hw_settings_yaml=hw_yaml),
            callback=self._on_hw_submit_result,
        )

    def _on_hw_submit_result(self, firmware: str | None) -> None:
        if firmware:
            from plugsmith.config import load_app_config
            cfg = load_app_config()
            cfg.hw_submitted_firmware = firmware
            cfg.save()
            self.refresh_stats()


class MainScreen(Screen):
    """Primary screen — always resident, single TabbedContent."""

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+b", "switch_tab('tab-build')", "Build"),
        Binding("ctrl+r", "switch_tab('tab-radio')", "Radio"),
        Binding("ctrl+e", "switch_tab('tab-config')", "Config"),
        Binding("ctrl+g", "switch_tab('tab-roaming')", "Roaming"),
        Binding("f1", "help", "Help"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield StatusBar()
        with TabbedContent(
            initial="tab-dashboard",
            id="main-tabs",
        ):
            with TabPane("Dashboard", id="tab-dashboard"):
                yield DashboardPane("Dashboard")
            with TabPane("Build", id="tab-build"):
                yield BuildPane()
            with TabPane("Radio", id="tab-radio"):
                yield RadioPane()
            with TabPane("Config", id="tab-config"):
                yield ConfigEditorPane()
            with TabPane("Roaming", id="tab-roaming"):
                yield RoamingPane()
        yield Footer()

    def on_mount(self) -> None:
        self._refresh_status_bar()
        # Load last tab from config
        from plugsmith.config import load_app_config
        cfg = load_app_config()
        if cfg.last_tab:
            try:
                self.query_one("#main-tabs", TabbedContent).active = cfg.last_tab
            except Exception:
                pass

    def _refresh_status_bar(self) -> None:
        from plugsmith.config import load_app_config
        cfg = load_app_config()
        bar = self.query_one(StatusBar)
        bar.refresh_dmrconf(cfg.dmrconf_path)
        bar.set_config_path(cfg.codeplug_config)

    def action_switch_tab(self, tab_id: str) -> None:
        self.query_one("#main-tabs", TabbedContent).active = tab_id

    def action_help(self) -> None:
        from plugsmith.screens.modals import ErrorModal
        self.app.push_screen(ErrorModal(
            "plugsmith Help",
            "Keyboard shortcuts:\n"
            "  Ctrl+Q — Quit\n"
            "  Ctrl+B — Build tab\n"
            "  Ctrl+R — Radio tab\n"
            "  Ctrl+E — Config tab\n"
            "  Ctrl+G — Roaming tab\n"
            "  F1     — This help\n\n"
            "Docs: https://github.com/yourusername/plugsmith",
        ))

    def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        from plugsmith.config import load_app_config
        cfg = load_app_config()
        cfg.last_tab = event.tab.id or "tab-dashboard"
        cfg.save()

    def on_build_pane_build_finished(self, msg: BuildPane.BuildFinished) -> None:
        if msg.success:
            try:
                self.query_one("DashboardPane", DashboardPane).refresh_stats()
            except Exception:
                pass
        else:
            from plugsmith.screens.modals import ErrorModal
            self.app.push_screen(ErrorModal("Build Failed", msg.error or "Unknown error"))
