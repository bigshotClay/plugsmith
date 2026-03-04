"""RadioPane — detect/read/write/verify/encode/decode/write-db via dmrconf subprocess."""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Button, Collapsible, Input, Label, Select, Static, Switch

from plugsmith.runner import SubprocessRunner
from plugsmith.widgets.field_editors import LabeledInput, LabeledSwitch
from plugsmith.widgets.output_log import OutputLog
from plugsmith.tool_discovery import list_radio_models

if TYPE_CHECKING:
    pass


ALL_BTNS = (
    "#btn-detect",
    "#btn-read-yaml",
    "#btn-read-dfu",
    "#btn-read-csv",
    "#btn-info",
    "#btn-verify",
    "#btn-write",
    "#btn-encode",
    "#btn-decode",
    "#btn-write-db",
    "#btn-encode-db",
)


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
    RadioPane Collapsible {
        margin-bottom: 1;
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
                yield Button("Read .csv", id="btn-read-csv", variant="default")
            with Horizontal(classes="btn-row"):
                yield Button("Info", id="btn-info", variant="default")
                yield Button("Verify", id="btn-verify", variant="default")
                yield Button("⚠ Write to Radio", id="btn-write", variant="warning")
            with Horizontal(classes="row"):
                yield Label("Backup dir:")
                yield Input(placeholder="backups/", id="input-backup-dir", value="backups")

            with Collapsible(title="Write Options", collapsed=False):
                yield LabeledSwitch("Init codeplug:", "lsw-init-codeplug", value=True)
                yield LabeledSwitch("Sync device clock:", "lsw-update-clock", value=False)
                yield LabeledSwitch("Auto-enable GPS:", "lsw-auto-gps", value=False)
                yield LabeledSwitch("Auto-enable roaming:", "lsw-auto-roaming", value=False)

            with Collapsible(title="Format Conversion", collapsed=True):
                yield LabeledInput("Source .dfu:", "input-decode-src", placeholder="path/to/backup.dfu")
                with Horizontal(classes="btn-row"):
                    yield Button("Encode .yaml→.dfu", id="btn-encode", variant="default")
                    yield Button("Decode .dfu→.yaml", id="btn-decode", variant="default")

            with Collapsible(title="Callsign Database", collapsed=True):
                yield LabeledInput("DMR ID:", "input-db-dmrid", placeholder="e.g. 3211477")
                yield LabeledInput("DB JSON path:", "input-db-path", placeholder="(use default BrandMeister)")
                yield LabeledInput("Max entries:", "input-db-limit", placeholder="(no limit)")
                with Horizontal(classes="btn-row"):
                    yield Button("Write DB to Radio", id="btn-write-db", variant="default")
                    yield Button("Encode DB to File", id="btn-encode-db", variant="default")

            yield Static("● No radio detected", id="radio-status", classes="status-line")
            yield OutputLog(id="radio-log")

    def on_mount(self) -> None:
        from plugsmith.config import load_app_config
        cfg = load_app_config()
        if cfg.device:
            self.query_one("#input-device", Input).value = cfg.device
        if cfg.backup_dir:
            self.query_one("#input-backup-dir", Input).value = cfg.backup_dir
        if cfg.radio_model:
            try:
                self.query_one("#select-radio-model", Select).value = cfg.radio_model
            except Exception:
                pass
        self.query_one("#lsw-init-codeplug", LabeledSwitch).value = cfg.init_codeplug
        self.query_one("#lsw-update-clock", LabeledSwitch).value = cfg.update_device_clock
        self.query_one("#lsw-auto-gps", LabeledSwitch).value = cfg.auto_enable_gps
        self.query_one("#lsw-auto-roaming", LabeledSwitch).value = cfg.auto_enable_roaming
        if cfg.callsign_db_path:
            self.query_one("#input-db-path", Input).value = cfg.callsign_db_path
        if cfg.callsign_limit:
            self.query_one("#input-db-limit", Input).value = str(cfg.callsign_limit)
        if cfg.dmr_id if hasattr(cfg, "dmr_id") else False:
            pass  # dmr_id lives in codeplug config.yaml, not plugsmith config

    def watch__running(self, val: bool) -> None:
        for btn_id in ALL_BTNS:
            try:
                self.query_one(btn_id, Button).disabled = val
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Config persistence helpers
    # ------------------------------------------------------------------

    @on(Switch.Changed)
    def _on_switch_changed(self, _: Switch.Changed) -> None:
        """Persist write-option switches to app config immediately."""
        from plugsmith.config import load_app_config
        cfg = load_app_config()
        cfg.init_codeplug = self.query_one("#lsw-init-codeplug", LabeledSwitch).value
        cfg.update_device_clock = self.query_one("#lsw-update-clock", LabeledSwitch).value
        cfg.auto_enable_gps = self.query_one("#lsw-auto-gps", LabeledSwitch).value
        cfg.auto_enable_roaming = self.query_one("#lsw-auto-roaming", LabeledSwitch).value
        cfg.save()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

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

    def _codeplug_path(self) -> str | None:
        """Return str path to codeplug.yaml, or None (and log) if missing."""
        from plugsmith.config import load_app_config
        cfg = load_app_config()
        p = str(cfg.codeplug_yaml_path)
        if not Path(p).exists():
            self._log(f"ERROR: Codeplug not found: {p}", is_err=True)
            return None
        return p

    def _db_dmrid(self) -> str:
        """DMR ID from DB section input (falls back to codeplug config)."""
        val = self.query_one("#input-db-dmrid", Input).value.strip()
        if val:
            return val
        from plugsmith.config import load_app_config
        cfg = load_app_config()
        # Try to read dmr_id from the codeplug config.yaml
        if cfg.codeplug_config_path and cfg.codeplug_config_path.exists():
            try:
                import yaml  # type: ignore[import-untyped]
                with open(cfg.codeplug_config_path) as f:
                    data = yaml.safe_load(f)
                return str(data.get("dmr_id", ""))
            except Exception:
                pass
        return ""

    # ------------------------------------------------------------------
    # Button handlers — device commands
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

    @on(Button.Pressed, "#btn-read-csv")
    def _read_csv(self) -> None:
        device = self._device()
        if not device:
            self._log("ERROR: No device path set.", is_err=True)
            return
        bd = self._backup_dir()
        bd.mkdir(parents=True, exist_ok=True)
        out = str(bd / self._auto_backup_name(".csv"))
        self._log(f"Reading CSV to {out}…")
        self._running = True
        self.run_command([self._dmrconf(), "read", "--device", device, "--csv", out])

    @on(Button.Pressed, "#btn-info")
    def _info(self) -> None:
        codeplug_path = self._codeplug_path()
        if not codeplug_path:
            return
        self._running = True
        self._set_status("Reading codeplug info…")
        self.run_command([self._dmrconf(), "info", codeplug_path])

    @on(Button.Pressed, "#btn-verify")
    def _verify(self) -> None:
        device = self._device()
        radio = self._radio_model()
        if not device or not radio:
            self._log("ERROR: Device and radio model are required.", is_err=True)
            return
        codeplug_path = self._codeplug_path()
        if not codeplug_path:
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
        codeplug_path = self._codeplug_path()
        if not codeplug_path:
            return

        from plugsmith.screens.modals import WriteAcknowledgeModal, ConfirmModal

        def _after_ack(acked: bool) -> None:
            if not acked:
                return
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

        self.app.push_screen(WriteAcknowledgeModal(), callback=_after_ack)

    def _do_write(self, confirmed: bool, device: str, radio: str, codeplug_path: str) -> None:
        if not confirmed:
            return
        self._running = True
        self._set_status("Writing to radio…")
        cmd = [self._dmrconf(), "write", "--radio", radio, "--device", device]
        if self.query_one("#lsw-init-codeplug", LabeledSwitch).value:
            cmd.append("--init-codeplug")
        if self.query_one("#lsw-update-clock", LabeledSwitch).value:
            cmd.append("--update-device-clock")
        if self.query_one("#lsw-auto-gps", LabeledSwitch).value:
            cmd.append("--auto-enable-gps")
        if self.query_one("#lsw-auto-roaming", LabeledSwitch).value:
            cmd.append("--auto-enable-roaming")
        cmd.append(codeplug_path)
        self._log(f"Running: {' '.join(cmd)}")
        self.run_command(cmd)

    # ------------------------------------------------------------------
    # Button handlers — format conversion
    # ------------------------------------------------------------------

    @on(Button.Pressed, "#btn-encode")
    def _encode(self) -> None:
        """Encode codeplug YAML → DFU binary (offline, no device needed)."""
        codeplug_path = self._codeplug_path()
        if not codeplug_path:
            return
        bd = self._backup_dir()
        bd.mkdir(parents=True, exist_ok=True)
        out_dfu = str(bd / self._auto_backup_name(".dfu"))
        self._log(f"Encoding {codeplug_path} → {out_dfu}…")
        self._running = True
        self.run_command([self._dmrconf(), "encode", "--bin", out_dfu, codeplug_path])

    @on(Button.Pressed, "#btn-decode")
    def _decode(self) -> None:
        """Decode DFU binary → YAML (offline, no device needed)."""
        src_dfu = self.query_one("#input-decode-src", Input).value.strip()
        if not src_dfu:
            self._log("ERROR: Set the source .dfu path in Format Conversion.", is_err=True)
            return
        if not Path(src_dfu).exists():
            self._log(f"ERROR: Source file not found: {src_dfu}", is_err=True)
            return
        bd = self._backup_dir()
        bd.mkdir(parents=True, exist_ok=True)
        out_yaml = str(bd / self._auto_backup_name(".yaml"))
        self._log(f"Decoding {src_dfu} → {out_yaml}…")
        self._running = True
        self.run_command([self._dmrconf(), "decode", "--yaml", out_yaml, src_dfu])

    # ------------------------------------------------------------------
    # Button handlers — callsign database
    # ------------------------------------------------------------------

    @on(Button.Pressed, "#btn-write-db")
    def _write_db(self) -> None:
        device = self._device()
        radio = self._radio_model()
        if not device or not radio:
            self._log("ERROR: Device and radio model are required.", is_err=True)
            return
        dmr_id = self._db_dmrid()
        if not dmr_id:
            self._log("ERROR: DMR ID is required for callsign DB operations.", is_err=True)
            return
        db_path = self.query_one("#input-db-path", Input).value.strip()
        limit_str = self.query_one("#input-db-limit", Input).value.strip()
        cmd = [
            self._dmrconf(), "write-db",
            "--device", device,
            "--radio", radio,
            "--id", dmr_id,
        ]
        if db_path:
            cmd += ["--database", db_path]
        if limit_str.isdigit() and int(limit_str) > 0:
            cmd += ["--limit", limit_str]
        self._running = True
        self._set_status("Writing callsign DB to radio…")
        self.run_command(cmd)

    @on(Button.Pressed, "#btn-encode-db")
    def _encode_db(self) -> None:
        dmr_id = self._db_dmrid()
        if not dmr_id:
            self._log("ERROR: DMR ID is required for callsign DB operations.", is_err=True)
            return
        bd = self._backup_dir()
        bd.mkdir(parents=True, exist_ok=True)
        out_file = str(bd / self._auto_backup_name("_db.json"))
        db_path = self.query_one("#input-db-path", Input).value.strip()
        limit_str = self.query_one("#input-db-limit", Input).value.strip()
        cmd = [self._dmrconf(), "encode-db", "--id", dmr_id]
        if db_path:
            cmd += ["--database", db_path]
        if limit_str.isdigit() and int(limit_str) > 0:
            cmd += ["--limit", limit_str]
        cmd.append(out_file)
        self._log(f"Encoding callsign DB to {out_file}…")
        self._running = True
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
            if "write-db" in msg.cmd or "encode-db" in msg.cmd:
                self._set_status("✓ Callsign DB operation complete")
            elif "write" in msg.cmd:
                self._set_status("✓ Write complete — radio is rebooting")
                self._log("Upload completed. Radio is rebooting — do not disconnect or re-run.")
            elif "detect" in msg.cmd:
                self._set_status("✓ Detected")
            elif "info" in msg.cmd:
                self._set_status("✓ Info complete")
            elif "encode" in msg.cmd or "decode" in msg.cmd:
                self._set_status("✓ Conversion complete")
            else:
                self._set_status(f"✓ Done (exit {msg.returncode})")
        else:
            self._set_status(f"✗ Failed (exit {msg.returncode})")
            self._log(f"Process exited with code {msg.returncode}", is_err=True)
