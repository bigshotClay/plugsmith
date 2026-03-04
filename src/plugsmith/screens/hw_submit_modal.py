"""HardwareSubmitModal — in-app form to submit hw config to GitHub Issues."""
from __future__ import annotations

import requests
from textual import on, work
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Static, TextArea


class HardwareSubmitModal(ModalScreen[str | None]):
    """Modal form for submitting hardware config to GitHub Issues.

    Returns firmware version string on success, None if skipped.
    """

    DEFAULT_CSS = """
    HardwareSubmitModal {
        align: center middle;
    }
    HardwareSubmitModal > Vertical {
        background: $panel;
        border: thick $primary;
        padding: 2 3;
        width: 72;
        height: auto;
    }
    HardwareSubmitModal .modal-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    HardwareSubmitModal .field-row {
        height: 3;
        margin-bottom: 1;
        align: left middle;
    }
    HardwareSubmitModal .field-row Label {
        width: 20;
        color: $text-muted;
    }
    HardwareSubmitModal .field-row Input {
        width: 1fr;
    }
    HardwareSubmitModal .section-label {
        color: $text-muted;
        margin-top: 1;
        margin-bottom: 1;
    }
    HardwareSubmitModal .nav-row {
        height: 3;
        margin-top: 2;
        align: right middle;
    }
    HardwareSubmitModal .nav-row Button {
        margin-left: 1;
    }
    HardwareSubmitModal .dim-info {
        color: $text-muted;
        margin-bottom: 1;
    }
    """

    def __init__(self, radio_key: str, hw_settings_yaml: str = "") -> None:
        super().__init__()
        self._radio_key = radio_key
        self._hw_settings_yaml = hw_settings_yaml

    def compose(self) -> ComposeResult:
        from plugsmith.tool_discovery import RADIO_PROFILES, DEFAULT_RADIO_PROFILE, builder_version
        profile = RADIO_PROFILES.get(self._radio_key, DEFAULT_RADIO_PROFILE)

        with Vertical():
            yield Label("Submit Hardware Config", classes="modal-title")
            yield Static(
                f"[dim]Radio: {profile.display_name} ({self._radio_key})[/dim]",
                markup=True,
                classes="dim-info",
            )
            with Horizontal(classes="field-row"):
                yield Label("Firmware version:")
                yield Input(
                    placeholder="e.g. 3.06",
                    id="hw-firmware",
                )
            with Horizontal(classes="field-row"):
                yield Label("Notes (optional):")
                yield Input(
                    placeholder="e.g. Works well, TX power limited",
                    id="hw-notes",
                )
            yield Label("Hardware settings (editable):", classes="section-label")
            yield TextArea(
                self._hw_settings_yaml,
                id="hw-settings-area",
                language="yaml",
            )
            yield Static(
                f"[dim]dmrconf: {builder_version()}[/dim]",
                markup=True,
                classes="dim-info",
            )
            with Horizontal(classes="nav-row"):
                yield Button("Submit", id="hw-btn-submit", variant="primary", disabled=True)
                yield Button("Skip", id="hw-btn-skip", variant="default")

    @on(Input.Changed, "#hw-firmware")
    def _on_firmware_changed(self, event: Input.Changed) -> None:
        self.query_one("#hw-btn-submit", Button).disabled = not event.value.strip()

    @on(Button.Pressed, "#hw-btn-skip")
    def _skip(self) -> None:
        self.dismiss(None)

    @on(Button.Pressed, "#hw-btn-submit")
    def _submit(self) -> None:
        firmware = self.query_one("#hw-firmware", Input).value.strip()
        notes = self.query_one("#hw-notes", Input).value.strip()
        hw_yaml = self.query_one("#hw-settings-area", TextArea).text
        self._do_submit(firmware, notes, hw_yaml)

    @work(thread=True)
    def _do_submit(self, firmware: str, notes: str, hw_yaml: str) -> None:
        from plugsmith.tool_discovery import RADIO_PROFILES, DEFAULT_RADIO_PROFILE, builder_version
        from plugsmith.hw_submit import submit_hw_profile

        profile = RADIO_PROFILES.get(self._radio_key, DEFAULT_RADIO_PROFILE)
        try:
            url = submit_hw_profile(
                radio_key=self._radio_key,
                display_name=profile.display_name,
                firmware_version=firmware,
                hw_settings_yaml=hw_yaml,
                notes=notes,
                dmrconf_version=builder_version(),
            )
            self.app.call_from_thread(
                self.notify,
                f"Issue created: {url}",
                severity="information",
                timeout=10,
            )
            self.app.call_from_thread(self.dismiss, firmware)
        except (requests.HTTPError, RuntimeError) as err:
            self.app.call_from_thread(
                self.notify,
                str(err),
                severity="error",
            )
