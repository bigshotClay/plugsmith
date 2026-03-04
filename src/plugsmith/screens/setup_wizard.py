"""SetupWizardScreen — 3-step first-run wizard."""

from __future__ import annotations

import time
from pathlib import Path

import yaml
from textual import on, work
from textual.app import ComposeResult
from textual.containers import Center, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, ContentSwitcher, Input, Label, Select, Static

from plugsmith.tool_discovery import (
    RADIO_PROFILES,
    detect_radio_model,
    list_radio_models,
    list_serial_devices,
)


class SetupWizardScreen(ModalScreen[bool]):
    """Three-step first-run setup: config → radio → confirm."""

    DEFAULT_CSS = """
    SetupWizardScreen {
        align: center middle;
    }
    SetupWizardScreen > Vertical {
        background: $panel;
        border: thick $primary;
        padding: 2 3;
        width: 70;
        height: auto;
        min-height: 20;
    }
    SetupWizardScreen .wizard-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    SetupWizardScreen .step-title {
        text-style: bold;
        margin-bottom: 1;
    }
    SetupWizardScreen .step-help {
        color: $text-muted;
        margin-bottom: 1;
    }
    SetupWizardScreen .row {
        height: 3;
        margin-bottom: 1;
        align: left middle;
    }
    SetupWizardScreen .row Label {
        width: 18;
        color: $text-muted;
    }
    SetupWizardScreen .row Input {
        width: 1fr;
    }
    SetupWizardScreen .nav-row {
        height: 3;
        margin-top: 2;
        align: right middle;
    }
    SetupWizardScreen .nav-row Button {
        margin-left: 1;
    }
    SetupWizardScreen .summary-row {
        margin-bottom: 1;
    }
    SetupWizardScreen .detect-row {
        height: 3;
        margin-bottom: 1;
        align: left middle;
    }
    SetupWizardScreen #wiz-detect-status {
        margin-left: 2;
        color: $text-muted;
    }
    SetupWizardScreen .detect-help {
        color: $text-muted;
        margin-bottom: 1;
    }
    SetupWizardScreen .section-label {
        text-style: bold;
        color: $text-muted;
        margin-top: 1;
        margin-bottom: 1;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._step = 0
        self._config_path = ""
        self._device = ""
        self._radio_model = ""

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("plugsmith Setup", classes="wizard-title")
            with ContentSwitcher(initial="step-0", id="wizard-switcher"):
                # Step 0: Locate config
                with Vertical(id="step-0"):
                    yield Label("Step 1 of 3 — Locate config.yaml", classes="step-title")
                    yield Static(
                        "Point plugsmith to your codeplug config.yaml. "
                        "If you don't have one yet, click [Create New].\n\n"
                        "[dim]You will need to add your email address to config.yaml "
                        "(api_email: you@example.com) before building — "
                        "RepeaterBook requires it in the API User-Agent.[/dim]",
                        classes="step-help",
                        markup=True,
                    )
                    with Horizontal(classes="row"):
                        yield Label("config.yaml:")
                        yield Input(placeholder="Path to config.yaml…", id="wiz-config-path")
                    with Horizontal(classes="row"):
                        yield Button("Browse…", id="wiz-browse-config", variant="default")
                        yield Button("Create New", id="wiz-create-config", variant="default")

                # Step 1: Radio setup
                with Vertical(id="step-1"):
                    yield Label("Step 2 of 3 — Radio Setup", classes="step-title")
                    yield Static(
                        "Auto-detect your radio by unplugging it first, then clicking "
                        "[b]Start Detection[/b] and plugging it back in.",
                        classes="detect-help",
                        markup=True,
                    )
                    with Horizontal(classes="detect-row"):
                        yield Button("Start Detection", id="wiz-detect-start", variant="primary")
                        yield Static("", id="wiz-detect-status")
                    yield Label("— or enter manually —", classes="section-label")
                    with Horizontal(classes="row"):
                        yield Label("Device path:")
                        yield Input(
                            placeholder="e.g. cu.usbmodem0000000100001",
                            id="wiz-device",
                        )
                    with Horizontal(classes="row"):
                        yield Label("Radio model:")
                        yield Select(
                            options=[(name, key) for key, name in list_radio_models()],
                            id="wiz-radio-model",
                            prompt="Select radio model…",
                        )

                # Step 2: Confirm
                with Vertical(id="step-2"):
                    yield Label("Step 3 of 3 — Confirm", classes="step-title")
                    yield Static("Review your settings, then click [Save & Launch].", classes="step-help")
                    yield Static("", id="wiz-summary")

            with Horizontal(classes="nav-row"):
                yield Button("Cancel", id="wiz-skip", variant="default")
                yield Button("Back", id="wiz-back", variant="default")
                yield Button("Next →", id="wiz-next", variant="primary")
                yield Button("Save & Launch", id="wiz-save", variant="success")

    def on_mount(self) -> None:
        self._update_nav()

    def _update_nav(self) -> None:
        switcher = self.query_one("#wizard-switcher", ContentSwitcher)
        switcher.current = f"step-{self._step}"
        self.query_one("#wiz-back", Button).display = self._step > 0
        self.query_one("#wiz-next", Button).display = self._step < 2
        self.query_one("#wiz-save", Button).display = self._step == 2
        if self._step == 2:
            self._refresh_summary()

    def _refresh_summary(self) -> None:
        lines = [
            f"[bold]Config:[/bold] {self._config_path or '(not set)'}",
            f"[bold]Device:[/bold] {self._device or '(not set)'}",
            f"[bold]Radio:[/bold] {self._radio_model or '(not set)'}",
        ]
        self.query_one("#wiz-summary", Static).update("\n".join(lines))

    @on(Button.Pressed, "#wiz-next")
    def _next_step(self) -> None:
        if self._step == 0:
            path = self.query_one("#wiz-config-path", Input).value.strip()
            if not path:
                self.notify("Please select or create a config.yaml first.", severity="warning")
                return
            self._config_path = path
        elif self._step == 1:
            self._device = self.query_one("#wiz-device", Input).value.strip()
            val = self.query_one("#wiz-radio-model", Select).value
            self._radio_model = str(val) if val and val != Select.BLANK else ""
        self._step = min(self._step + 1, 2)
        self._update_nav()

    @on(Button.Pressed, "#wiz-back")
    def _prev_step(self) -> None:
        self._step = max(self._step - 1, 0)
        self._update_nav()

    @on(Button.Pressed, "#wiz-detect-start")
    def _start_detection(self) -> None:
        self.query_one("#wiz-detect-start", Button).disabled = True
        self._set_detect_status("Scanning current devices…")
        self._run_detection_worker()

    @work(thread=True)
    def _run_detection_worker(self) -> None:
        snapshot = set(list_serial_devices())
        self.app.call_from_thread(self._set_detect_status, "Plug in your radio now…")
        deadline = time.monotonic() + 30.0
        while time.monotonic() < deadline:
            time.sleep(0.5)
            current = set(list_serial_devices())
            new = current - snapshot
            if new:
                device = sorted(new)[0]
                self.app.call_from_thread(self._on_device_found, device)
                return
        self.app.call_from_thread(self._on_detection_timeout)

    def _on_device_found(self, device: str) -> None:
        self.query_one("#wiz-device", Input).value = device
        self._set_detect_status(f"Found {device} — identifying radio…")
        self._identify_radio_worker(device)

    @work(thread=True)
    def _identify_radio_worker(self, device: str) -> None:
        from plugsmith.config import load_app_config
        cfg = load_app_config()
        model_key = detect_radio_model(device, cfg.dmrconf_path)
        self.app.call_from_thread(self._on_radio_identified, device, model_key)

    def _on_radio_identified(self, device: str, model_key: str | None) -> None:
        if model_key and model_key in RADIO_PROFILES:
            display = RADIO_PROFILES[model_key].display_name
            self._set_detect_status(f"[green]✓ {device} — {display}[/green]")
            select = self.query_one("#wiz-radio-model", Select)
            select.value = model_key
        else:
            self._set_detect_status(
                f"[green]✓ {device} found[/green] — select radio model below",
            )
        self.query_one("#wiz-detect-start", Button).disabled = False

    def _on_detection_timeout(self) -> None:
        self._set_detect_status(
            "[red]✗ No device detected. Enter path manually below.[/red]",
        )
        self.query_one("#wiz-detect-start", Button).disabled = False

    def _set_detect_status(self, text: str) -> None:
        self.query_one("#wiz-detect-status", Static).update(text)

    @on(Button.Pressed, "#wiz-browse-config")
    def _browse_config(self) -> None:
        from plugsmith.screens.modals import FilePickerModal
        self.app.push_screen(
            FilePickerModal(title="Select config.yaml"),
            callback=lambda p: self._set_config_path(p),
        )

    def _set_config_path(self, path: object) -> None:
        if path:
            self.query_one("#wiz-config-path", Input).value = str(path)
            self._config_path = str(path)
            self._step = 1
            self._update_nav()

    @on(Button.Pressed, "#wiz-create-config")
    def _create_config(self) -> None:
        from plugsmith.builder.build_config import write_default_config

        default_path = Path.home() / "codeplug" / "config.yaml"
        default_path.parent.mkdir(parents=True, exist_ok=True)
        write_default_config(str(default_path))
        self.query_one("#wiz-config-path", Input).value = str(default_path)
        self._config_path = str(default_path)
        self.notify(f"Created: {default_path}", severity="information")
        self._step = 1
        self._update_nav()

    @on(Button.Pressed, "#wiz-save")
    def _save_and_launch(self) -> None:
        # Collect last step's values
        self._device = self.query_one("#wiz-device", Input).value.strip()
        val = self.query_one("#wiz-radio-model", Select).value
        self._radio_model = str(val) if val and val != Select.BLANK else ""

        from plugsmith.config import load_app_config
        cfg = load_app_config()
        cfg.codeplug_config = self._config_path
        cfg.device = self._device
        cfg.radio_model = self._radio_model
        cfg.save()

        from plugsmith.hw_submit import is_submission_needed
        if is_submission_needed(self._radio_model, cfg.hw_submitted_firmware):
            from plugsmith.screens.hw_submit_modal import HardwareSubmitModal
            self.app.push_screen(
                HardwareSubmitModal(self._radio_model),
                callback=self._on_hw_submit_result,
            )
        else:
            self.dismiss(True)

    def _on_hw_submit_result(self, firmware: str | None) -> None:
        if firmware:
            from plugsmith.config import load_app_config
            cfg = load_app_config()
            cfg.hw_submitted_firmware = firmware
            cfg.save()
        self.dismiss(True)

    @on(Button.Pressed, "#wiz-skip")
    def _skip(self) -> None:
        self.dismiss(False)
