"""SetupWizardScreen — 3-step first-run wizard."""

from __future__ import annotations

from pathlib import Path

import yaml
from textual import on
from textual.app import ComposeResult
from textual.containers import Center, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, ContentSwitcher, Input, Label, Select, Static

from plugsmith.tool_discovery import list_radio_models


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
                        "Enter your radio's USB device path and select the model.",
                        classes="step-help",
                    )
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
                yield Button("Back", id="wiz-back", variant="default")
                yield Button("Next →", id="wiz-next", variant="primary")
                yield Button("Save & Launch", id="wiz-save", variant="success")
                yield Button("Skip", id="wiz-skip", variant="default")

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
            if path:
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

    @on(Button.Pressed, "#wiz-create-config")
    def _create_config(self) -> None:
        from plugsmith.builder.build_config import write_default_config
        from plugsmith.screens.modals import FilePickerModal

        # Default to home directory
        default_path = Path.home() / "codeplug" / "config.yaml"
        default_path.parent.mkdir(parents=True, exist_ok=True)
        write_default_config(str(default_path))
        self.query_one("#wiz-config-path", Input).value = str(default_path)
        self.notify(f"Created: {default_path}", severity="information")

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
        self.dismiss(True)

    @on(Button.Pressed, "#wiz-skip")
    def _skip(self) -> None:
        self.dismiss(False)
