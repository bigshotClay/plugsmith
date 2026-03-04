"""RadioPane — detect/read/write/verify via dmrconf subprocess."""

from __future__ import annotations

import datetime
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Button, Input, Label, Select, Static

from plugsmith.runner import SubprocessRunner
from plugsmith.widgets.output_log import OutputLog
from plugsmith.tool_discovery import list_radio_models

if TYPE_CHECKING:
    pass


class RadioPane(Widget, SubprocessRunner):
    """Tab pane: radio operations via dmrconf."""

    DEFAULT_CSS = """
    RadioPane {
        padding: 1 2;
    }
    RadioPane .row {
        height: 3;
        margin-bottom: 1;
        align: left middle;
    }
    RadioPane .row Label {
        width: 10;
        color: $text-muted;
    }
    RadioPane .row Input {
        width: 1fr;
    }
    RadioPane .row Select {
        width: 1fr;
    }
    RadioPane .btn-row {
        height: 3;
        margin-bottom: 1;
    }
    RadioPane .btn-row Button {
        margin-right: 1;
    }
    RadioPane .status-line {
        height: 1;
        margin-bottom: 1;
        color: $text-muted;
    }
    """

    _running: reactive[bool] = reactive(False)

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("[bold]Radio Operations[/bold]")
            with Horizontal(classes="row"):
                yield Label("Device:")
                yield Input(placeholder="e.g. cu.usbmodem0000000100001", id="input-device")
            with Horizontal(classes="row"):
                yield Label("Radio:")
                yield Select(
                    options=[(name, key) for key, name in list_radio_models()],
                    id="select-radio-model",
                    prompt="Select radio model…",
                )
            with Horizontal(classes="btn-row"):
                yield Button("Detect", id="btn-detect", variant="default")
                yield Button("Read .yaml", id="btn-read-yaml", variant="default")
                yield Button("Read .dfu", id="btn-read-dfu", variant="default")
            with Horizontal(classes="btn-row"):
                yield Button("Verify", id="btn-verify", variant="default")
                yield Button("⚠ Write to Radio", id="btn-write", variant="warning")
            with Horizontal(classes="row"):
                yield Label("Backup dir:")
                yield Input(placeholder="backups/", id="input-backup-dir", value="backups")
            yield Static("● No radio detected", id="radio-status", classes="status-line")
            yield OutputLog(id="radio-log")

    def on_mount(self) -> None:
        from plugsmith.config import load_app_config
        cfg = load_app_config()
        if cfg.device:
            self.query_one("#input-device", Input).value = cfg.device
        if cfg.backup_dir:
            self.query_one("#input-backup-dir", Input).value = cfg.backup_dir
        # Pre-select radio model
        if cfg.radio_model:
            try:
                self.query_one("#select-radio-model", Select).value = cfg.radio_model
            except Exception:
                pass

    def watch__running(self, val: bool) -> None:
        for btn_id in ("#btn-detect", "#btn-read-yaml", "#btn-read-dfu", "#btn-verify", "#btn-write"):
            try:
                self.query_one(btn_id, Button).disabled = val
            except Exception:
                pass

    def _device(self) -> str:
        return self.query_one("#input-device", Input).value.strip()

    def _radio_model(self) -> str:
        val = self.query_one("#select-radio-model", Select).value
        return str(val) if val and val != Select.BLANK else ""

    def _backup_dir(self) -> Path:
        bd = self.query_one("#input-backup-dir", Input).value.strip() or "backups"
        from plugsmith.config import load_app_config
        cfg = load_app_config()
        base = Path(cfg.codeplug_config).parent if cfg.codeplug_config else Path(".")
        p = Path(bd)
        return p if p.is_absolute() else base / p

    def _dmrconf(self) -> str:
        from plugsmith.config import load_app_config
        from plugsmith.tool_discovery import find_dmrconf
        cfg = load_app_config()
        status = find_dmrconf(cfg.dmrconf_path)
        if status.found and status.path:
            return str(status.path)
        return "dmrconf"

    def _auto_backup_name(self, ext: str) -> str:
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"878uvii_{ts}{ext}"

    def _set_status(self, msg: str) -> None:
        self.query_one("#radio-status", Static).update(msg)

    def _log(self, msg: str, is_err: bool = False) -> None:
        self.query_one("#radio-log", OutputLog).write_line(msg, "red" if is_err else None)

    # ------------------------------------------------------------------
    # Button handlers
    # ------------------------------------------------------------------

    @on(Button.Pressed, "#btn-detect")
    def _detect(self) -> None:
        device = self._device()
        if not device:
            self._log("ERROR: No device path set.", is_err=True)
            return
        self._running = True
        self._set_status("Detecting radio…")
        self.run_command([self._dmrconf(), "detect", "--device", device])

    @on(Button.Pressed, "#btn-read-yaml")
    def _read_yaml(self) -> None:
        device = self._device()
        if not device:
            self._log("ERROR: No device path set.", is_err=True)
            return
        bd = self._backup_dir()
        bd.mkdir(parents=True, exist_ok=True)
        out = str(bd / self._auto_backup_name(".yaml"))
        self._log(f"Reading YAML to {out}…")
        self._running = True
        self.run_command([self._dmrconf(), "read", "--device", device, "--yaml", out])

    @on(Button.Pressed, "#btn-read-dfu")
    def _read_dfu(self) -> None:
        device = self._device()
        if not device:
            self._log("ERROR: No device path set.", is_err=True)
            return
        bd = self._backup_dir()
        bd.mkdir(parents=True, exist_ok=True)
        out = str(bd / self._auto_backup_name(".dfu"))
        self._log(f"Reading DFU binary to {out}…")
        self._running = True
        self.run_command([self._dmrconf(), "read", "--device", device, "--bin", out])

    @on(Button.Pressed, "#btn-verify")
    def _verify(self) -> None:
        device = self._device()
        radio = self._radio_model()
        if not device or not radio:
            self._log("ERROR: Device and radio model are required.", is_err=True)
            return
        from plugsmith.config import load_app_config
        cfg = load_app_config()
        codeplug_path = str(cfg.codeplug_yaml_path)
        if not Path(codeplug_path).exists():
            self._log(f"ERROR: Codeplug not found: {codeplug_path}", is_err=True)
            return
        self._running = True
        self._set_status("Verifying…")
        self.run_command([
            self._dmrconf(), "verify",
            "--radio", radio,
            "--device", device,
            codeplug_path,
        ])

    @on(Button.Pressed, "#btn-write")
    def _write_prompt(self) -> None:
        device = self._device()
        radio = self._radio_model()
        if not device or not radio:
            self._log("ERROR: Device and radio model are required.", is_err=True)
            return
        from plugsmith.config import load_app_config
        cfg = load_app_config()
        codeplug_path = str(cfg.codeplug_yaml_path)
        if not Path(codeplug_path).exists():
            self._log(f"ERROR: Codeplug not found: {codeplug_path}", is_err=True)
            return

        from plugsmith.screens.modals import ConfirmModal
        self.app.push_screen(
            ConfirmModal(
                f"Write [bold]{codeplug_path}[/bold] to radio [bold]{radio}[/bold] "
                f"on device [bold]{device}[/bold]?\n\n"
                "The radio will reboot after write. Do NOT disconnect or re-run.",
                title="Write to Radio",
                danger=True,
            ),
            callback=lambda confirmed: self._do_write(confirmed, device, radio, codeplug_path),
        )

    def _do_write(self, confirmed: bool, device: str, radio: str, codeplug_path: str) -> None:
        if not confirmed:
            return
        self._running = True
        self._set_status("Writing to radio…")
        cmd = [
            self._dmrconf(), "write",
            "--radio", radio,
            "--device", device,
            "--init-codeplug",
            codeplug_path,
        ]
        self._log(f"Running: {' '.join(cmd)}")
        self.run_command(cmd)

    # ------------------------------------------------------------------
    # SubprocessRunner message handlers
    # ------------------------------------------------------------------

    def on_subprocess_runner_output_line(self, msg: SubprocessRunner.OutputLine) -> None:
        self.query_one("#radio-log", OutputLog).write_line(
            msg.line, "yellow" if msg.is_stderr else None
        )

    def on_subprocess_runner_process_started(self, msg: SubprocessRunner.ProcessStarted) -> None:
        self._log(f"$ {' '.join(msg.cmd)}")

    def on_subprocess_runner_process_finished(self, msg: SubprocessRunner.ProcessFinished) -> None:
        self._running = False
        if msg.returncode == 0:
            # Check if this was a write command
            if "write" in msg.cmd:
                self._set_status("✓ Write complete — radio is rebooting")
                self._log("Upload completed. Radio is rebooting — do not disconnect or re-run.")
            elif "detect" in msg.cmd:
                self._set_status("✓ Detected")
            else:
                self._set_status(f"✓ Done (exit {msg.returncode})")
        else:
            self._set_status(f"✗ Failed (exit {msg.returncode})")
            self._log(f"Process exited with code {msg.returncode}", is_err=True)
