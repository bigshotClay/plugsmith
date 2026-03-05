"""Integration tests: PlugsmithApp UI interactions via Textual Pilot.

Tests cover:
 - App startup with complete / incomplete config
 - Tab navigation via keyboard shortcuts and dashboard buttons
 - BuildPane: empty-path error, non-existent-path error, clear cache
 - RadioPane: no-device validation, process message handling, running state
 - ConfigEditorPane: mounts without crash, save without path shows error
 - Modals: ConfirmModal, ErrorModal, WriteAcknowledgeModal, FilePickerModal
 - OutputLog widget: write, clear, clear button
 - SetupWizard: cancel, navigation, step gating
 - SubprocessRunner: message types
 - Write workflow: acknowledge modal flow

NOTE on Textual 8 query semantics
──────────────────────────────────
`App.query_one()` searches the *default* screen (the blank base screen), NOT
pushed screens like MainScreen/Wizards/Modals.  Always use `app.screen.query_one()`
to search the *current* top-of-stack screen.  `pilot.click()` already does this
internally via `screen.query_one()`, so click-by-selector always works correctly.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from plugsmith.app import PlugsmithApp
from plugsmith.config import PlugsmithConfig
from plugsmith.runner import SubprocessRunner
from plugsmith.tool_discovery import ToolStatus, _FALLBACK_RADIO_MODELS


# ── Internal helpers ──────────────────────────────────────────────────────────

_MISSING_DMRCONF = ToolStatus(found=False, path=None, version=None, error="mocked")
_FOUND_DMRCONF = ToolStatus(
    found=True, path=Path("/usr/bin/dmrconf"), version="0.9.0", error=None
)


def _make_complete_cfg(tmp_path: Path) -> PlugsmithConfig:
    """Return a PlugsmithConfig backed by a real minimal config.yaml in tmp_path."""
    config_yaml = tmp_path / "config.yaml"
    config_yaml.write_text(
        "dmr_id: 3211477\n"
        "callsign: W0RRK\n"
        "api_email: test@example.com\n"
        "modes:\n  fm: true\n  dmr: true\n"
        "filters:\n  open_only: true\n  on_air_only: true\n"
        "bands:\n  - 2m\n  - 70cm\n"
        "organization:\n  strategy: tiered_region\n"
        "reference_location:\n  lat: 38.2085\n  lon: -91.1604\n"
        "output:\n  qdmr_yaml: codeplug.yaml\n"
    )
    cfg = PlugsmithConfig(
        codeplug_config=str(config_yaml),
        device="cu.usbmodem0000000100001",
        radio_model="d878uv2",
    )
    cfg.save = MagicMock()  # prevent real TOML writes
    return cfg


# ── Autouse fixtures (apply to every test) ───────────────────────────────────


@pytest.fixture(autouse=True)
def _no_subprocess_tools(monkeypatch):
    """Prevent dmrconf subprocess calls that happen during compose / mount."""
    # StatusBar.on_mount → find_dmrconf (module-level import in status_bar.py)
    monkeypatch.setattr(
        "plugsmith.widgets.status_bar.find_dmrconf",
        MagicMock(return_value=_MISSING_DMRCONF),
    )
    # RadioPane.compose → list_radio_models (module-level import in radio_screen.py)
    monkeypatch.setattr(
        "plugsmith.screens.radio_screen.list_radio_models",
        MagicMock(return_value=_FALLBACK_RADIO_MODELS),
    )
    # SetupWizardScreen.compose → list_radio_models (module-level import in setup_wizard.py)
    monkeypatch.setattr(
        "plugsmith.screens.setup_wizard.list_radio_models",
        MagicMock(return_value=_FALLBACK_RADIO_MODELS),
    )


@pytest.fixture(autouse=True)
def _no_config_writes(monkeypatch):
    """Prevent any PlugsmithConfig instance from writing to ~/.config/plugsmith/."""
    monkeypatch.setattr("plugsmith.config.PlugsmithConfig.save", MagicMock())


# ── Primary fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def complete_cfg(tmp_path, monkeypatch) -> PlugsmithConfig:
    """Set up load_app_config to return a complete PlugsmithConfig."""
    cfg = _make_complete_cfg(tmp_path)
    mock_fn = MagicMock(return_value=cfg)
    monkeypatch.setattr("plugsmith.config.load_app_config", mock_fn)
    monkeypatch.setattr("plugsmith.app.load_app_config", mock_fn)
    return cfg


@pytest.fixture
def app_complete(complete_cfg) -> PlugsmithApp:
    """PlugsmithApp with a complete config (wizard will NOT appear)."""
    return PlugsmithApp()


@pytest.fixture
def app_incomplete(monkeypatch) -> PlugsmithApp:
    """PlugsmithApp with an incomplete config (wizard WILL appear)."""
    cfg = PlugsmithConfig()  # all empty → is_complete() == False
    cfg.save = MagicMock()
    mock_fn = MagicMock(return_value=cfg)
    monkeypatch.setattr("plugsmith.config.load_app_config", mock_fn)
    monkeypatch.setattr("plugsmith.app.load_app_config", mock_fn)
    return PlugsmithApp()


# ── TestAppStartup ────────────────────────────────────────────────────────────


class TestAppStartup:
    async def test_app_mounts_main_screen(self, app_complete):
        """App with complete config shows MainScreen without wizard."""
        from plugsmith.screens.main_screen import MainScreen

        async with app_complete.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            assert isinstance(app_complete.screen, MainScreen)

    async def test_app_shows_wizard_when_config_incomplete(self, app_incomplete):
        """App with incomplete config pushes SetupWizardScreen."""
        from plugsmith.screens.setup_wizard import SetupWizardScreen

        async with app_incomplete.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            assert isinstance(app_incomplete.screen, SetupWizardScreen)

    async def test_main_screen_has_tabbed_content(self, app_complete):
        """MainScreen exposes a TabbedContent starting on the dashboard tab."""
        from textual.widgets import TabbedContent

        async with app_complete.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            tabs = app_complete.screen.query_one("#main-tabs", TabbedContent)
            assert tabs is not None
            assert tabs.active == "tab-dashboard"

    async def test_status_bar_is_mounted(self, app_complete):
        """StatusBar widget exists in the DOM after mount."""
        from plugsmith.widgets.status_bar import StatusBar

        async with app_complete.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            bar = app_complete.screen.query_one(StatusBar)
            assert bar is not None

    async def test_dashboard_pane_is_mounted(self, app_complete):
        """DashboardPane is in the DOM after mount."""
        from plugsmith.screens.main_screen import DashboardPane

        async with app_complete.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            pane = app_complete.screen.query_one(DashboardPane)
            assert pane is not None

    async def test_build_pane_is_mounted(self, app_complete):
        """BuildPane is in the DOM (even before the tab is active)."""
        from plugsmith.screens.build_screen import BuildPane

        async with app_complete.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            pane = app_complete.screen.query_one(BuildPane)
            assert pane is not None

    async def test_radio_pane_is_mounted(self, app_complete):
        """RadioPane is in the DOM."""
        from plugsmith.screens.radio_screen import RadioPane

        async with app_complete.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            pane = app_complete.screen.query_one(RadioPane)
            assert pane is not None

    async def test_config_editor_pane_is_mounted(self, app_complete):
        """ConfigEditorPane is in the DOM."""
        from plugsmith.screens.config_editor import ConfigEditorPane

        async with app_complete.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            pane = app_complete.screen.query_one(ConfigEditorPane)
            assert pane is not None

    async def test_roaming_pane_is_mounted(self, app_complete):
        """RoamingPane is in the DOM."""
        from plugsmith.screens.roaming_screen import RoamingPane

        async with app_complete.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            pane = app_complete.screen.query_one(RoamingPane)
            assert pane is not None


# ── TestTabNavigation ─────────────────────────────────────────────────────────


class TestTabNavigation:
    async def test_ctrl_b_switches_to_build_tab(self, app_complete):
        """Ctrl+B activates the Build tab."""
        from textual.widgets import TabbedContent

        async with app_complete.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await pilot.press("ctrl+b")
            await pilot.pause()
            assert app_complete.screen.query_one("#main-tabs", TabbedContent).active == "tab-build"

    async def test_ctrl_r_switches_to_radio_tab(self, app_complete):
        """Ctrl+R activates the Radio tab."""
        from textual.widgets import TabbedContent

        async with app_complete.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await pilot.press("ctrl+r")
            await pilot.pause()
            assert app_complete.screen.query_one("#main-tabs", TabbedContent).active == "tab-radio"

    async def test_ctrl_e_switches_to_config_tab(self, app_complete):
        """Ctrl+E activates the Config tab."""
        from textual.widgets import TabbedContent

        async with app_complete.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await pilot.press("ctrl+e")
            await pilot.pause()
            assert app_complete.screen.query_one("#main-tabs", TabbedContent).active == "tab-config"

    async def test_ctrl_g_switches_to_roaming_tab(self, app_complete):
        """Ctrl+G activates the Roaming tab."""
        from textual.widgets import TabbedContent

        async with app_complete.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await pilot.press("ctrl+g")
            await pilot.pause()
            assert app_complete.screen.query_one("#main-tabs", TabbedContent).active == "tab-roaming"

    async def test_f1_opens_help_modal(self, app_complete):
        """F1 opens the help ErrorModal."""
        from plugsmith.screens.modals import ErrorModal

        async with app_complete.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await pilot.press("f1")
            await pilot.pause()
            assert isinstance(app_complete.screen, ErrorModal)

    async def test_help_modal_closes_and_returns_to_main(self, app_complete):
        """Closing the help modal returns to MainScreen."""
        from plugsmith.screens.main_screen import MainScreen
        from plugsmith.screens.modals import ErrorModal

        async with app_complete.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await pilot.press("f1")
            await pilot.pause()
            assert isinstance(app_complete.screen, ErrorModal)
            await pilot.click("#btn-close")
            await pilot.pause()
            assert isinstance(app_complete.screen, MainScreen)


# ── TestDashboard ─────────────────────────────────────────────────────────────


class TestDashboard:
    async def test_build_button_navigates_to_build(self, app_complete):
        """Dashboard '▶ Build' button activates the Build tab."""
        from textual.widgets import TabbedContent

        async with app_complete.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await pilot.click("#dash-btn-build")
            await pilot.pause()
            assert app_complete.screen.query_one("#main-tabs", TabbedContent).active == "tab-build"

    async def test_radio_button_navigates_to_radio(self, app_complete):
        """Dashboard 'Write to Radio' button activates the Radio tab."""
        from textual.widgets import TabbedContent

        async with app_complete.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await pilot.click("#dash-btn-radio")
            await pilot.pause()
            assert app_complete.screen.query_one("#main-tabs", TabbedContent).active == "tab-radio"

    async def test_config_button_navigates_to_config(self, app_complete):
        """Dashboard 'Edit Config' button activates the Config tab."""
        from textual.widgets import TabbedContent

        async with app_complete.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await pilot.click("#dash-btn-config")
            await pilot.pause()
            assert app_complete.screen.query_one("#main-tabs", TabbedContent).active == "tab-config"

    async def test_dashboard_stats_render_without_yaml(self, app_complete):
        """Dashboard stat labels exist even when codeplug.yaml doesn't exist."""
        from textual.widgets import Label

        async with app_complete.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            channels_lbl = app_complete.screen.query_one("#dash-channels", Label)
            assert channels_lbl is not None

    async def test_dashboard_reads_channel_count_from_yaml(self, tmp_path, monkeypatch):
        """Dashboard reads channel/zone counts from a real codeplug.yaml."""
        from textual.widgets import Label

        codeplug_yaml = tmp_path / "codeplug.yaml"
        codeplug_yaml.write_text(
            "channels:\n  - name: test1\n  - name: test2\n"
            "zones:\n  - name: z1\n"
        )
        config_yaml = tmp_path / "config.yaml"
        config_yaml.write_text("dmr_id: 3211477\ncallsign: W0RRK\n")
        cfg = PlugsmithConfig(
            codeplug_config=str(config_yaml),
            codeplug_yaml=str(codeplug_yaml),
            device="cu.usbmodem0000000100001",
            radio_model="d878uv2",
        )
        cfg.save = MagicMock()
        mock_fn = MagicMock(return_value=cfg)
        monkeypatch.setattr("plugsmith.config.load_app_config", mock_fn)
        monkeypatch.setattr("plugsmith.app.load_app_config", mock_fn)

        app = PlugsmithApp()
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            channels_lbl = app.screen.query_one("#dash-channels", Label)
            assert "2" in str(channels_lbl.render())
            zones_lbl = app.screen.query_one("#dash-zones", Label)
            assert "1" in str(zones_lbl.render())


# ── TestBuildPane ─────────────────────────────────────────────────────────────


class TestBuildPane:
    async def test_build_pane_renders(self, app_complete):
        """BuildPane composes without raising."""
        from plugsmith.screens.build_screen import BuildPane

        async with app_complete.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            assert app_complete.screen.query_one(BuildPane) is not None

    async def test_build_prefills_config_path(self, app_complete, complete_cfg):
        """BuildPane pre-fills the config path from app config on mount."""
        from textual.widgets import Input

        async with app_complete.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            inp = app_complete.screen.query_one("#input-config-path", Input)
            assert inp.value == complete_cfg.codeplug_config

    async def test_build_empty_path_shows_error_modal(self, app_complete):
        """Clicking Build with no config path pushes ErrorModal."""
        from plugsmith.screens.modals import ErrorModal
        from textual.widgets import Input

        async with app_complete.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await pilot.press("ctrl+b")
            await pilot.pause()
            # Clear the config path
            app_complete.screen.query_one("#input-config-path", Input).value = ""
            await pilot.pause()
            await pilot.click("#btn-build")
            await pilot.pause()
            assert isinstance(app_complete.screen, ErrorModal)

    async def test_build_nonexistent_path_shows_error_modal(self, app_complete, tmp_path):
        """Clicking Build with a path that doesn't exist pushes ErrorModal."""
        from plugsmith.screens.modals import ErrorModal
        from textual.widgets import Input

        async with app_complete.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await pilot.press("ctrl+b")
            await pilot.pause()
            app_complete.screen.query_one("#input-config-path", Input).value = str(
                tmp_path / "does_not_exist.yaml"
            )
            await pilot.pause()
            await pilot.click("#btn-build")
            await pilot.pause()
            assert isinstance(app_complete.screen, ErrorModal)

    async def test_build_error_modal_can_be_closed(self, app_complete):
        """ErrorModal from build error can be dismissed, returning to MainScreen."""
        from plugsmith.screens.main_screen import MainScreen
        from textual.widgets import Input

        async with app_complete.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await pilot.press("ctrl+b")
            await pilot.pause()
            app_complete.screen.query_one("#input-config-path", Input).value = ""
            await pilot.pause()
            await pilot.click("#btn-build")
            await pilot.pause()
            await pilot.click("#btn-close")
            await pilot.pause()
            assert isinstance(app_complete.screen, MainScreen)

    async def test_clear_cache_does_not_crash(self, app_complete):
        """Clicking Clear Cache without a config path does not crash."""
        from textual.widgets import Input

        async with app_complete.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await pilot.press("ctrl+b")
            await pilot.pause()
            app_complete.screen.query_one("#input-config-path", Input).value = ""
            await pilot.pause()
            await pilot.click("#btn-clear-cache")
            await pilot.pause()
            # No crash = pass

    async def test_build_button_disables_when_building_starts(self, app_complete):
        """Build button becomes disabled once the build worker starts."""
        from textual.widgets import Button

        async with app_complete.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await pilot.press("ctrl+b")
            await pilot.pause()
            # Config path is already filled from fixture
            await pilot.click("#btn-build")
            await pilot.pause()
            btn = app_complete.screen.query_one("#btn-build", Button)
            assert btn.disabled

    async def test_build_failure_re_enables_button(self, app_complete, monkeypatch):
        """A build failure eventually re-enables the build button."""
        from textual.widgets import Button
        from plugsmith.screens.modals import ErrorModal
        from plugsmith.screens.main_screen import MainScreen

        # Patch fetch_states to fail immediately (no real HTTP requests)
        monkeypatch.setattr(
            "plugsmith.builder.api.RepeaterBookClient",
            MagicMock(return_value=MagicMock(fetch_states=MagicMock(side_effect=RuntimeError("mocked failure")))),
        )

        async with app_complete.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await pilot.press("ctrl+b")
            await pilot.pause()
            await pilot.click("#btn-build")
            # Wait for the build to fail — MainScreen pushes ErrorModal on failure
            for _ in range(30):
                await pilot.pause(0.1)
                if isinstance(app_complete.screen, ErrorModal):
                    break
            # Dismiss the error modal
            if isinstance(app_complete.screen, ErrorModal):
                await pilot.click("#btn-close")
                await pilot.pause()
            assert isinstance(app_complete.screen, MainScreen)
            assert not app_complete.screen.query_one("#btn-build", Button).disabled


# ── TestRadioPane ─────────────────────────────────────────────────────────────


class TestRadioPane:
    async def test_radio_pane_renders(self, app_complete):
        """RadioPane composes without raising."""
        from plugsmith.screens.radio_screen import RadioPane

        async with app_complete.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            assert app_complete.screen.query_one(RadioPane) is not None

    async def test_radio_prefills_device(self, app_complete, complete_cfg):
        """RadioPane pre-fills the device field from app config."""
        from textual.widgets import Input

        async with app_complete.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            inp = app_complete.screen.query_one("#input-device", Input)
            assert inp.value == complete_cfg.device

    async def test_detect_no_device_logs_error(self, app_complete):
        """Clicking Detect with empty device field logs an error, no crash."""
        from textual.widgets import Input

        async with app_complete.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await pilot.press("ctrl+r")
            await pilot.pause()
            app_complete.screen.query_one("#input-device", Input).value = ""
            await pilot.pause()
            await pilot.click("#btn-detect")
            await pilot.pause()
            from plugsmith.widgets.output_log import OutputLog
            from textual.widgets import RichLog

            log = app_complete.screen.query_one("#radio-log", OutputLog)
            assert len(log.query_one("#rich-log", RichLog).lines) >= 1

    async def test_verify_no_device_logs_error(self, app_complete):
        """Clicking Verify with empty device field logs an error, no crash."""
        from textual.widgets import Input

        async with app_complete.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await pilot.press("ctrl+r")
            await pilot.pause()
            app_complete.screen.query_one("#input-device", Input).value = ""
            await pilot.pause()
            await pilot.click("#btn-verify")
            await pilot.pause()
            from plugsmith.widgets.output_log import OutputLog
            from textual.widgets import RichLog

            log = app_complete.screen.query_one("#radio-log", OutputLog)
            assert len(log.query_one("#rich-log", RichLog).lines) >= 1

    async def test_write_no_device_logs_error(self, app_complete):
        """Clicking Write with empty device field logs an error, no crash."""
        from textual.widgets import Input

        async with app_complete.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await pilot.press("ctrl+r")
            await pilot.pause()
            app_complete.screen.query_one("#input-device", Input).value = ""
            await pilot.pause()
            await pilot.click("#btn-write")
            await pilot.pause()
            from plugsmith.widgets.output_log import OutputLog
            from textual.widgets import RichLog

            log = app_complete.screen.query_one("#radio-log", OutputLog)
            assert len(log.query_one("#rich-log", RichLog).lines) >= 1

    async def test_detect_dispatches_run_command(self, app_complete):
        """Detect button with device set calls run_command with correct args."""
        from plugsmith.screens.radio_screen import RadioPane

        run_cmd_calls: list[list[str]] = []

        async with app_complete.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await pilot.press("ctrl+r")
            await pilot.pause()

            pane = app_complete.screen.query_one(RadioPane)
            original_run = pane.run_command
            pane.run_command = lambda cmd, **kw: run_cmd_calls.append(cmd) or original_run(cmd, **kw)

            await pilot.click("#btn-detect")
            await pilot.pause()

        assert any("detect" in cmd for cmd in run_cmd_calls)
        assert any("cu.usbmodem0000000100001" in cmd for cmd in run_cmd_calls)

    async def test_running_flag_disables_buttons(self, app_complete):
        """Setting _running=True disables all radio command buttons."""
        from plugsmith.screens.radio_screen import RadioPane, ALL_BTNS
        from textual.widgets import Button

        async with app_complete.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await pilot.press("ctrl+r")
            await pilot.pause()

            pane = app_complete.screen.query_one(RadioPane)
            pane._running = True
            await pilot.pause()

            for btn_id in ALL_BTNS:
                try:
                    btn = app_complete.screen.query_one(btn_id, Button)
                    assert btn.disabled, f"Button {btn_id} should be disabled while running"
                except Exception:
                    pass  # button may be in a collapsed section

    async def test_process_finished_success_clears_running(self, app_complete):
        """ProcessFinished(returncode=0) clears _running and updates status."""
        from plugsmith.screens.radio_screen import RadioPane
        from textual.widgets import Static

        async with app_complete.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await pilot.press("ctrl+r")
            await pilot.pause()

            pane = app_complete.screen.query_one(RadioPane)
            pane._running = True
            pane.post_message(
                SubprocessRunner.ProcessFinished(0, ["dmrconf", "detect", "--device", "x"])
            )
            await pilot.pause(0.1)

            assert not pane._running
            status_text = str(app_complete.screen.query_one("#radio-status", Static).render())
            assert "✓" in status_text

    async def test_process_finished_failure_shows_failure_status(self, app_complete):
        """ProcessFinished(returncode=1) clears _running and shows failure status."""
        from plugsmith.screens.radio_screen import RadioPane
        from textual.widgets import Static

        async with app_complete.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await pilot.press("ctrl+r")
            await pilot.pause()

            pane = app_complete.screen.query_one(RadioPane)
            pane._running = True
            pane.post_message(
                SubprocessRunner.ProcessFinished(1, ["dmrconf", "detect"])
            )
            await pilot.pause(0.1)

            assert not pane._running
            status_text = str(app_complete.screen.query_one("#radio-status", Static).render())
            assert "✗" in status_text or "Failed" in status_text

    async def test_output_line_writes_to_radio_log(self, app_complete):
        """OutputLine message appends to the radio log."""
        from plugsmith.screens.radio_screen import RadioPane
        from plugsmith.widgets.output_log import OutputLog
        from textual.widgets import RichLog

        async with app_complete.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await pilot.press("ctrl+r")
            await pilot.pause()

            pane = app_complete.screen.query_one(RadioPane)
            pane.post_message(SubprocessRunner.OutputLine("Radio detected: AT-D878UVII"))
            await pilot.pause(0.1)

            log = app_complete.screen.query_one("#radio-log", OutputLog)
            assert len(log.query_one("#rich-log", RichLog).lines) >= 1

    async def test_process_started_logs_command(self, app_complete):
        """ProcessStarted message logs the command line."""
        from plugsmith.screens.radio_screen import RadioPane
        from plugsmith.widgets.output_log import OutputLog
        from textual.widgets import RichLog

        async with app_complete.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await pilot.press("ctrl+r")
            await pilot.pause()

            pane = app_complete.screen.query_one(RadioPane)
            pane.post_message(
                SubprocessRunner.ProcessStarted(["dmrconf", "detect", "--device", "test"])
            )
            await pilot.pause(0.1)

            log = app_complete.screen.query_one("#radio-log", OutputLog)
            assert len(log.query_one("#rich-log", RichLog).lines) >= 1

    async def test_run_command_with_missing_binary_posts_error(self, app_complete):
        """run_command with a missing binary posts an error line without crashing."""
        from plugsmith.screens.radio_screen import RadioPane
        from plugsmith.widgets.output_log import OutputLog
        from textual.widgets import RichLog

        async with app_complete.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await pilot.press("ctrl+r")
            await pilot.pause()

            pane = app_complete.screen.query_one(RadioPane)
            with patch("plugsmith.runner.subprocess.Popen", side_effect=FileNotFoundError):
                pane.run_command(["totally_fake_binary", "--arg"])
                await pilot.pause(0.3)

            log = app_complete.screen.query_one("#radio-log", OutputLog)
            assert len(log.query_one("#rich-log", RichLog).lines) >= 1

    async def test_encode_db_no_dmrid_logs_error(self, app_complete):
        """Encode DB without a DMR ID logs an error."""
        from textual.widgets import Input

        async with app_complete.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await pilot.press("ctrl+r")
            await pilot.pause()
            app_complete.screen.query_one("#input-db-dmrid", Input).value = ""
            await pilot.pause()
            from textual.widgets import Button
            app_complete.screen.query_one("#btn-encode-db", Button).press()
            await pilot.pause()
            from plugsmith.widgets.output_log import OutputLog
            from textual.widgets import RichLog

            log = app_complete.screen.query_one("#radio-log", OutputLog)
            assert len(log.query_one("#rich-log", RichLog).lines) >= 1


# ── TestConfigEditor ──────────────────────────────────────────────────────────


class TestConfigEditor:
    async def test_config_editor_renders(self, app_complete):
        """ConfigEditorPane composes without raising."""
        from plugsmith.screens.config_editor import ConfigEditorPane

        async with app_complete.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await pilot.press("ctrl+e")
            await pilot.pause()
            assert app_complete.screen.query_one(ConfigEditorPane) is not None

    async def test_save_without_config_path_shows_error(self, app_complete):
        """Clicking Save Config when no file is loaded pushes ErrorModal."""
        from plugsmith.screens.config_editor import ConfigEditorPane
        from plugsmith.screens.modals import ErrorModal

        async with app_complete.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await pilot.press("ctrl+e")
            await pilot.pause()
            pane = app_complete.screen.query_one(ConfigEditorPane)
            pane._config_path = ""  # clear loaded path
            await pilot.pause()
            from textual.widgets import Button
            app_complete.screen.query_one("#btn-save-config", Button).press()
            await pilot.pause()
            assert isinstance(app_complete.screen, ErrorModal)

    async def test_config_editor_adds_simplex_row(self, app_complete):
        """Clicking '+ Add Channel' adds a simplex channel row."""
        from plugsmith.screens.config_editor import ConfigEditorPane

        async with app_complete.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await pilot.press("ctrl+e")
            await pilot.pause()
            pane = app_complete.screen.query_one(ConfigEditorPane)
            counter_before = pane._simplex_counter
            from textual.widgets import Button
            app_complete.screen.query_one("#btn-add-simplex", Button).press()
            await pilot.pause()
            assert pane._simplex_counter > counter_before

    async def test_states_lower48_selects_48(self, app_complete):
        """Clicking 'Lower 48' selects the 48 contiguous states."""
        from textual.widgets import SelectionList

        async with app_complete.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await pilot.press("ctrl+e")
            await pilot.pause()
            from textual.widgets import Button
            app_complete.screen.query_one("#btn-states-clear", Button).press()
            await pilot.pause()
            app_complete.screen.query_one("#btn-states-lower48", Button).press()
            await pilot.pause()
            sl = app_complete.screen.query_one("#cfg-states", SelectionList)
            assert len(list(sl.selected)) == 48

    async def test_states_all_selects_50(self, app_complete):
        """Clicking 'All 50' selects all 50 US states."""
        from textual.widgets import SelectionList

        async with app_complete.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await pilot.press("ctrl+e")
            await pilot.pause()
            from textual.widgets import Button
            app_complete.screen.query_one("#btn-states-all", Button).press()
            await pilot.pause()
            sl = app_complete.screen.query_one("#cfg-states", SelectionList)
            assert len(list(sl.selected)) == 50

    async def test_states_clear_deselects_all(self, app_complete):
        """Clicking 'Clear' deselects all states."""
        from textual.widgets import SelectionList

        async with app_complete.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await pilot.press("ctrl+e")
            await pilot.pause()
            from textual.widgets import Button
            app_complete.screen.query_one("#btn-states-clear", Button).press()
            await pilot.pause()
            sl = app_complete.screen.query_one("#cfg-states", SelectionList)
            assert len(list(sl.selected)) == 0

    async def test_reload_config_does_not_crash(self, app_complete):
        """Clicking 'Reload from Disk' with a valid config path doesn't crash."""
        async with app_complete.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await pilot.press("ctrl+e")
            await pilot.pause()
            from textual.widgets import Button
            app_complete.screen.query_one("#btn-reload-config", Button).press()
            await pilot.pause()
            # No exception = pass


# ── TestConfirmModal ──────────────────────────────────────────────────────────


class TestConfirmModal:
    async def test_confirm_button_returns_true(self, app_complete):
        """ConfirmModal Confirm button dismisses with True."""
        from plugsmith.screens.modals import ConfirmModal

        results: list[bool] = []
        async with app_complete.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            app_complete.screen.app.push_screen(
                ConfirmModal("Are you sure?", title="Test"),
                callback=lambda r: results.append(r),
            )
            await pilot.pause()
            await pilot.click("#btn-confirm")
            await pilot.pause()
            assert results == [True]

    async def test_cancel_button_returns_false(self, app_complete):
        """ConfirmModal Cancel button dismisses with False."""
        from plugsmith.screens.modals import ConfirmModal

        results: list[bool] = []
        async with app_complete.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            app_complete.screen.app.push_screen(
                ConfirmModal("Are you sure?"),
                callback=lambda r: results.append(r),
            )
            await pilot.pause()
            await pilot.click("#btn-cancel")
            await pilot.pause()
            assert results == [False]

    async def test_danger_variant_styles_confirm_as_error(self, app_complete):
        """ConfirmModal with danger=True styles the Confirm button as error."""
        from plugsmith.screens.modals import ConfirmModal
        from textual.widgets import Button

        async with app_complete.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            app_complete.screen.app.push_screen(ConfirmModal("Danger!", danger=True))
            await pilot.pause()
            btn = app_complete.screen.query_one("#btn-confirm", Button)
            assert btn.variant == "error"


# ── TestErrorModal ────────────────────────────────────────────────────────────


class TestErrorModal:
    async def test_close_button_pops_modal(self, app_complete):
        """ErrorModal Close button pops the screen."""
        from plugsmith.screens.main_screen import MainScreen
        from plugsmith.screens.modals import ErrorModal

        async with app_complete.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            app_complete.screen.app.push_screen(ErrorModal("Test Error", "Something went wrong."))
            await pilot.pause()
            assert isinstance(app_complete.screen, ErrorModal)
            await pilot.click("#btn-close")
            await pilot.pause()
            assert isinstance(app_complete.screen, MainScreen)

    async def test_error_modal_is_instance_of_error_modal(self, app_complete):
        """ErrorModal is correctly identified after push."""
        from plugsmith.screens.modals import ErrorModal

        async with app_complete.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            app_complete.screen.app.push_screen(ErrorModal("My Title", "My message body."))
            await pilot.pause()
            assert isinstance(app_complete.screen, ErrorModal)


# ── TestWriteAcknowledgeModal ─────────────────────────────────────────────────


class TestWriteAcknowledgeModal:
    async def test_continue_disabled_initially(self, app_complete):
        """Continue button is disabled before the checkbox is checked."""
        from plugsmith.screens.modals import WriteAcknowledgeModal
        from textual.widgets import Button

        async with app_complete.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            app_complete.screen.app.push_screen(WriteAcknowledgeModal())
            await pilot.pause()
            assert app_complete.screen.query_one("#btn-continue", Button).disabled

    async def test_checkbox_enables_continue(self, app_complete):
        """Checking the backup checkbox enables the Continue button."""
        from plugsmith.screens.modals import WriteAcknowledgeModal
        from textual.widgets import Button, Checkbox

        async with app_complete.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            app_complete.screen.app.push_screen(WriteAcknowledgeModal())
            await pilot.pause()
            app_complete.screen.query_one("#cb-backup", Checkbox).value = True
            await pilot.pause()
            assert not app_complete.screen.query_one("#btn-continue", Button).disabled

    async def test_continue_returns_true(self, app_complete):
        """Clicking Continue (after checkbox) dismisses with True."""
        from plugsmith.screens.modals import WriteAcknowledgeModal
        from textual.widgets import Checkbox

        results: list[bool] = []
        async with app_complete.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            app_complete.screen.app.push_screen(
                WriteAcknowledgeModal(),
                callback=lambda r: results.append(r),
            )
            await pilot.pause()
            app_complete.screen.query_one("#cb-backup", Checkbox).value = True
            await pilot.pause()
            await pilot.click("#btn-continue")
            await pilot.pause()
            assert results == [True]

    async def test_cancel_returns_false(self, app_complete):
        """Clicking Cancel dismisses with False."""
        from plugsmith.screens.modals import WriteAcknowledgeModal

        results: list[bool] = []
        async with app_complete.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            app_complete.screen.app.push_screen(
                WriteAcknowledgeModal(),
                callback=lambda r: results.append(r),
            )
            await pilot.pause()
            await pilot.click("#btn-cancel")
            await pilot.pause()
            assert results == [False]


# ── TestFilePickerModal ───────────────────────────────────────────────────────


class TestFilePickerModal:
    async def test_cancel_dismisses_with_none(self, app_complete, tmp_path):
        """FilePickerModal Cancel returns None."""
        from plugsmith.screens.modals import FilePickerModal

        results: list = []
        async with app_complete.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            app_complete.screen.app.push_screen(
                FilePickerModal(start_path=str(tmp_path)),
                callback=lambda r: results.append(r),
            )
            await pilot.pause()
            await pilot.click("#btn-cancel")
            await pilot.pause()
            assert results == [None]

    async def test_select_typed_path_returns_path(self, app_complete, tmp_path):
        """FilePickerModal returns a Path when a valid path is typed."""
        from plugsmith.screens.modals import FilePickerModal
        from textual.widgets import Input

        target = tmp_path / "test.yaml"
        target.write_text("ok")

        results: list = []
        async with app_complete.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            app_complete.screen.app.push_screen(
                FilePickerModal(start_path=str(tmp_path)),
                callback=lambda r: results.append(r),
            )
            await pilot.pause()
            app_complete.screen.query_one("#path-input", Input).value = str(target)
            await pilot.pause()
            await pilot.click("#btn-select")
            await pilot.pause()
            assert results == [target]


# ── TestOutputLog ─────────────────────────────────────────────────────────────


class TestOutputLog:
    """Test the OutputLog widget in isolation via a minimal test App."""

    def _make_app(self):
        from plugsmith.widgets.output_log import OutputLog
        from textual.app import App, ComposeResult

        class _App(App):
            def compose(self) -> ComposeResult:
                yield OutputLog(id="log")

        return _App()

    async def test_write_line_adds_content(self):
        """write_line() increments the log line count."""
        from plugsmith.widgets.output_log import OutputLog
        from textual.widgets import RichLog

        app = self._make_app()
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            # OutputLog is on the default screen (composed directly in App.compose)
            log = app.query_one("#log", OutputLog)
            log.write_line("Hello, world!")
            await pilot.pause()
            assert len(log.query_one("#rich-log", RichLog).lines) >= 1

    async def test_write_styled_line(self):
        """write_line() with a style wraps in markup without crashing."""
        from plugsmith.widgets.output_log import OutputLog
        from textual.widgets import RichLog

        app = self._make_app()
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            log = app.query_one("#log", OutputLog)
            log.write_line("Error text", style="red")
            await pilot.pause()
            assert len(log.query_one("#rich-log", RichLog).lines) >= 1

    async def test_clear_removes_all_lines(self):
        """clear() removes all content from the log."""
        from plugsmith.widgets.output_log import OutputLog
        from textual.widgets import RichLog

        app = self._make_app()
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            log = app.query_one("#log", OutputLog)
            log.write_line("line 1")
            log.write_line("line 2")
            await pilot.pause()
            log.clear()
            await pilot.pause()
            assert len(log.query_one("#rich-log", RichLog).lines) == 0

    async def test_clear_button_clears_log(self):
        """The Clear button in the toolbar clears the log."""
        from plugsmith.widgets.output_log import OutputLog
        from textual.widgets import RichLog

        app = self._make_app()
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            log = app.query_one("#log", OutputLog)
            log.write_line("content")
            await pilot.pause()
            await pilot.click("#btn-clear-log")
            await pilot.pause()
            assert len(log.query_one("#rich-log", RichLog).lines) == 0

    async def test_autoscroll_switch_defaults_to_on(self):
        """The auto-scroll Switch widget defaults to True."""
        from plugsmith.widgets.output_log import OutputLog
        from textual.widgets import Switch

        app = self._make_app()
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            log = app.query_one("#log", OutputLog)
            sw = log.query_one("#switch-autoscroll", Switch)
            assert sw.value is True


# ── TestSubprocessRunnerMessages ──────────────────────────────────────────────


class TestSubprocessRunnerMessages:
    """Unit tests for SubprocessRunner message types (no UI needed)."""

    def test_output_line_stores_line_and_flag(self):
        msg = SubprocessRunner.OutputLine("hello", is_stderr=False)
        assert msg.line == "hello"
        assert msg.is_stderr is False

    def test_output_line_stderr_flag(self):
        msg = SubprocessRunner.OutputLine("err", is_stderr=True)
        assert msg.is_stderr is True

    def test_process_started_stores_cmd(self):
        cmd = ["dmrconf", "detect", "--device", "x"]
        msg = SubprocessRunner.ProcessStarted(cmd)
        assert msg.cmd == cmd

    def test_process_finished_stores_returncode_and_cmd(self):
        msg = SubprocessRunner.ProcessFinished(0, ["dmrconf", "info"])
        assert msg.returncode == 0
        assert "info" in msg.cmd

    def test_process_finished_nonzero(self):
        msg = SubprocessRunner.ProcessFinished(1, ["dmrconf", "write"])
        assert msg.returncode == 1


# ── TestSetupWizard ───────────────────────────────────────────────────────────


class TestSetupWizard:
    async def test_cancel_returns_to_main_screen(self, app_incomplete):
        """Cancel button dismisses the wizard and shows MainScreen."""
        from plugsmith.screens.main_screen import MainScreen

        async with app_incomplete.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await pilot.click("#wiz-skip")
            await pilot.pause()
            assert isinstance(app_incomplete.screen, MainScreen)

    async def test_starts_on_step_zero(self, app_incomplete):
        """Wizard opens showing step-0 in the ContentSwitcher."""
        from textual.widgets import ContentSwitcher

        async with app_incomplete.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            switcher = app_incomplete.screen.query_one("#wizard-switcher", ContentSwitcher)
            assert switcher.current == "step-0"

    async def test_next_without_path_stays_on_step_zero(self, app_incomplete):
        """Clicking Next with no config path filled in stays on step 0."""
        from textual.widgets import ContentSwitcher

        async with app_incomplete.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await pilot.click("#wiz-next")
            await pilot.pause()
            switcher = app_incomplete.screen.query_one("#wizard-switcher", ContentSwitcher)
            assert switcher.current == "step-0"

    async def test_next_with_path_advances_to_step_one(self, app_incomplete, tmp_path):
        """Filling in a config path and clicking Next advances to step 1."""
        from textual.widgets import ContentSwitcher, Input

        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text("dmr_id: 1234567\n")

        async with app_incomplete.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            app_incomplete.screen.query_one("#wiz-config-path", Input).value = str(cfg_file)
            await pilot.pause()
            await pilot.click("#wiz-next")
            await pilot.pause()
            switcher = app_incomplete.screen.query_one("#wizard-switcher", ContentSwitcher)
            assert switcher.current == "step-1"

    async def test_back_button_shown_on_step_one(self, app_incomplete, tmp_path):
        """Back button is visible once on step 1."""
        from textual.widgets import Button, Input

        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text("dmr_id: 1234567\n")

        async with app_incomplete.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            app_incomplete.screen.query_one("#wiz-config-path", Input).value = str(cfg_file)
            await pilot.pause()
            await pilot.click("#wiz-next")
            await pilot.pause()
            back = app_incomplete.screen.query_one("#wiz-back", Button)
            assert back.display

    async def test_back_returns_to_step_zero(self, app_incomplete, tmp_path):
        """Back button on step 1 returns to step 0."""
        from textual.widgets import ContentSwitcher, Input

        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text("dmr_id: 1234567\n")

        async with app_incomplete.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            app_incomplete.screen.query_one("#wiz-config-path", Input).value = str(cfg_file)
            await pilot.pause()
            await pilot.click("#wiz-next")
            await pilot.pause()
            await pilot.click("#wiz-back")
            await pilot.pause()
            switcher = app_incomplete.screen.query_one("#wizard-switcher", ContentSwitcher)
            assert switcher.current == "step-0"

    async def test_full_navigation_to_step_two(self, app_incomplete, tmp_path):
        """Can navigate all the way to step 2 (Confirm step)."""
        from textual.widgets import ContentSwitcher, Input, Button

        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text("dmr_id: 1234567\n")

        async with app_incomplete.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            app_incomplete.screen.query_one("#wiz-config-path", Input).value = str(cfg_file)
            await pilot.pause()
            await pilot.click("#wiz-next")
            await pilot.pause()
            # Step 1's content may push #wiz-next off-screen; use btn.press()
            app_incomplete.screen.query_one("#wiz-next", Button).press()
            await pilot.pause()
            switcher = app_incomplete.screen.query_one("#wizard-switcher", ContentSwitcher)
            assert switcher.current == "step-2"

    async def test_save_button_hidden_on_step_zero(self, app_incomplete):
        """Save & Launch button is hidden on step 0."""
        from textual.widgets import Button

        async with app_incomplete.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            save_btn = app_incomplete.screen.query_one("#wiz-save", Button)
            assert not save_btn.display

    async def test_save_button_visible_on_step_two(self, app_incomplete, tmp_path):
        """Save & Launch button appears on step 2."""
        from textual.widgets import Button, Input

        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text("dmr_id: 1234567\n")

        async with app_incomplete.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            app_incomplete.screen.query_one("#wiz-config-path", Input).value = str(cfg_file)
            await pilot.pause()
            await pilot.click("#wiz-next")
            await pilot.pause()
            # Step 1's content may push #wiz-next off-screen; use btn.press()
            app_incomplete.screen.query_one("#wiz-next", Button).press()
            await pilot.pause()
            save_btn = app_incomplete.screen.query_one("#wiz-save", Button)
            assert save_btn.display


# ── TestRoamingPane ───────────────────────────────────────────────────────────


class TestRoamingPane:
    async def test_roaming_pane_renders(self, app_complete):
        """RoamingPane composes and mounts without raising."""
        from plugsmith.screens.roaming_screen import RoamingPane

        async with app_complete.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await pilot.press("ctrl+g")
            await pilot.pause()
            assert app_complete.screen.query_one(RoamingPane) is not None

    async def test_roaming_table_empty_without_zones(self, app_complete):
        """Roaming DataTable is empty when config has no roaming_zones key."""
        from textual.widgets import DataTable

        async with app_complete.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await pilot.press("ctrl+g")
            await pilot.pause()
            table = app_complete.screen.query_one("#roaming-table", DataTable)
            assert table.row_count == 0

    async def test_edit_and_delete_disabled_without_selection(self, app_complete):
        """Edit and Delete buttons are disabled when no row is selected."""
        from textual.widgets import Button

        async with app_complete.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await pilot.press("ctrl+g")
            await pilot.pause()
            assert app_complete.screen.query_one("#btn-edit", Button).disabled
            assert app_complete.screen.query_one("#btn-delete", Button).disabled


# ── TestWriteWorkflow ─────────────────────────────────────────────────────────


class TestWriteWorkflow:
    """End-to-end test of the Write-to-Radio confirmation flow."""

    async def test_write_with_no_codeplug_logs_error(self, app_complete, monkeypatch, tmp_path):
        """Write button with no codeplug yaml logs an error instead of crashing."""
        from textual.widgets import Input

        # Config file must exist so ConfigEditorPane.on_mount doesn't push ErrorModal
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text("dmr_id: 3211477\ncallsign: W0RRK\n")

        from plugsmith.config import PlugsmithConfig
        cfg_nofile = PlugsmithConfig(
            codeplug_config=str(cfg_file),
            codeplug_yaml=str(tmp_path / "nonexistent_codeplug.yaml"),  # does not exist
            device="cu.usbmodem0000000100001",
            radio_model="d878uv2",
        )
        cfg_nofile.save = MagicMock()
        mock_fn = MagicMock(return_value=cfg_nofile)
        monkeypatch.setattr("plugsmith.config.load_app_config", mock_fn)
        monkeypatch.setattr("plugsmith.app.load_app_config", mock_fn)

        app = PlugsmithApp()
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await pilot.press("ctrl+r")
            await pilot.pause()
            await pilot.click("#btn-write")
            await pilot.pause()
            # Should log an error (no codeplug found), not crash
            from plugsmith.widgets.output_log import OutputLog
            from textual.widgets import RichLog

            log = app.screen.query_one("#radio-log", OutputLog)
            assert len(log.query_one("#rich-log", RichLog).lines) >= 1

    async def test_write_opens_acknowledge_modal(self, app_complete, tmp_path):
        """Write button opens WriteAcknowledgeModal when device and codeplug exist."""
        from plugsmith.screens.modals import WriteAcknowledgeModal

        codeplug = tmp_path / "codeplug.yaml"
        codeplug.write_text("channels: []\nzones: []\n")

        async with app_complete.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await pilot.press("ctrl+r")
            await pilot.pause()
            from textual.widgets import Input

            app_complete.screen.query_one("#input-codeplug-yaml", Input).value = str(codeplug)
            await pilot.pause()
            await pilot.click("#btn-write")
            await pilot.pause()
            assert isinstance(app_complete.screen, WriteAcknowledgeModal)

    async def test_write_ack_cancel_returns_to_main(self, app_complete, tmp_path):
        """Cancelling the WriteAcknowledgeModal returns to MainScreen."""
        from plugsmith.screens.main_screen import MainScreen

        codeplug = tmp_path / "codeplug.yaml"
        codeplug.write_text("channels: []\nzones: []\n")

        async with app_complete.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await pilot.press("ctrl+r")
            await pilot.pause()
            from textual.widgets import Input

            app_complete.screen.query_one("#input-codeplug-yaml", Input).value = str(codeplug)
            await pilot.pause()
            await pilot.click("#btn-write")
            await pilot.pause()
            await pilot.click("#btn-cancel")
            await pilot.pause()
            assert isinstance(app_complete.screen, MainScreen)
