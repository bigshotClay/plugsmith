"""BuildPane — run the bundled codeplug builder with live progress."""

from __future__ import annotations

import datetime
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from textual import on, work
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Button, Input, Label, ProgressBar, Static

from plugsmith.widgets.output_log import OutputLog

if TYPE_CHECKING:
    pass

log = logging.getLogger(__name__)


class BuildPane(Widget):
    """Tab pane: build a codeplug using the bundled builder."""

    class BuildFinished(Message):
        def __init__(self, success: bool, channel_count: int = 0, zone_count: int = 0, error: str = "") -> None:
            super().__init__()
            self.success = success
            self.channel_count = channel_count
            self.zone_count = zone_count
            self.error = error

    DEFAULT_CSS = """
    BuildPane {
        padding: 1 2;
    }
    BuildPane .row {
        height: 3;
        margin-bottom: 1;
        align: left middle;
    }
    BuildPane .row Label {
        width: 10;
        color: $text-muted;
    }
    BuildPane .row Input {
        width: 1fr;
    }
    BuildPane .btn-row {
        height: 3;
        margin-bottom: 1;
    }
    BuildPane .btn-row Button {
        margin-right: 1;
    }
    BuildPane ProgressBar {
        margin-bottom: 1;
    }
    BuildPane .status-line {
        height: 1;
        margin-bottom: 1;
        color: $text-muted;
    }
    """

    _building: reactive[bool] = reactive(False)

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("[bold]Build Codeplug[/bold]")
            with Horizontal(classes="row"):
                yield Label("Config:")
                yield Input(placeholder="Path to config.yaml…", id="input-config-path")
                yield Button("Browse", id="btn-browse-config", variant="default")
            with Horizontal(classes="row"):
                yield Label("Output:")
                yield Input(placeholder="codeplug.yaml", id="input-output-path")
            with Horizontal(classes="btn-row"):
                yield Button("▶ Build Codeplug", id="btn-build", variant="primary")
                yield Button("Clear Cache", id="btn-clear-cache", variant="default")
            yield ProgressBar(total=None, id="build-progress", show_eta=False)
            yield Static("", id="build-status", classes="status-line")
            yield OutputLog(id="build-log")

    def on_mount(self) -> None:
        self.query_one("#build-progress", ProgressBar).display = False
        # Pre-fill from app config
        from plugsmith.config import load_app_config
        cfg = load_app_config()
        if cfg.codeplug_config:
            self.query_one("#input-config-path", Input).value = cfg.codeplug_config
        if cfg.codeplug_yaml:
            self.query_one("#input-output-path", Input).value = cfg.codeplug_yaml

    def watch__building(self, val: bool) -> None:
        self.query_one("#btn-build", Button).disabled = val
        self.query_one("#build-progress", ProgressBar).display = val

    @on(Button.Pressed, "#btn-browse-config")
    def _browse_config(self) -> None:
        from plugsmith.screens.modals import FilePickerModal
        self.app.push_screen(
            FilePickerModal(title="Select config.yaml"),
            callback=lambda p: self._set_config_path(p),
        )

    def _set_config_path(self, path: object) -> None:
        if path:
            self.query_one("#input-config-path", Input).value = str(path)

    @on(Button.Pressed, "#btn-clear-cache")
    def _clear_cache(self) -> None:
        from plugsmith.config import load_app_config
        from plugsmith.builder.api import RepeaterBookClient
        cfg = load_app_config()
        config_path = self.query_one("#input-config-path", Input).value.strip()
        cache_dir = ".rb_cache"
        if config_path:
            from plugsmith.builder.build_config import load_config
            try:
                builder_cfg = load_config(config_path)
                cache_dir = builder_cfg.get("cache_dir", ".rb_cache")
                if not Path(cache_dir).is_absolute():
                    cache_dir = str(Path(config_path).parent / cache_dir)
            except Exception:
                pass
        client = RepeaterBookClient(cache_dir=cache_dir)
        count = client.clear_cache()
        log_widget = self.query_one("#build-log", OutputLog)
        log_widget.write_line(f"Cleared {count} cache files from {cache_dir}")

    @on(Button.Pressed, "#btn-build")
    def _start_build(self) -> None:
        config_path = self.query_one("#input-config-path", Input).value.strip()
        if not config_path:
            from plugsmith.screens.modals import ErrorModal
            self.app.push_screen(ErrorModal("No Config", "Please select a config.yaml file first."))
            return
        if not Path(config_path).exists():
            from plugsmith.screens.modals import ErrorModal
            self.app.push_screen(ErrorModal("File Not Found", f"Config file not found:\n{config_path}"))
            return

        output_path = self.query_one("#input-output-path", Input).value.strip()
        if not output_path:
            output_path = str(Path(config_path).parent / "codeplug.yaml")
            self.query_one("#input-output-path", Input).value = output_path

        log_widget = self.query_one("#build-log", OutputLog)
        log_widget.clear()
        self._building = True
        self._run_build(config_path, output_path)

    @work(thread=True)
    def _run_build(self, config_path: str, output_path: str) -> None:
        """Run the bundled builder in a background thread, posting progress messages."""
        from plugsmith.builder.build_config import load_config
        from plugsmith.builder.api import RepeaterBookClient, US_STATES
        from plugsmith.builder.filters import parse_repeaters, filter_repeaters, calculate_distances, classify_states, compute_state_ctcss_map, compute_state_input_freq_map
        from plugsmith.builder.zones import organize_zones_tiered, STATE_TGS_DEFAULT
        from plugsmith.builder.codeplug import generate_codeplug_yaml
        from plugsmith.builder.export import write_qdmr_yaml, write_anytone_csv, write_summary

        def post_line(msg: str, is_err: bool = False) -> None:
            self.call_from_thread(
                self.query_one("#build-log", OutputLog).write_line,
                msg,
                "red" if is_err else None,
            )

        def set_status(msg: str) -> None:
            self.call_from_thread(
                self.query_one("#build-status", Static).update,
                msg,
            )

        try:
            post_line(f"Loading config: {config_path}")
            config = load_config(config_path)
            dmr_id = config["dmr_id"]
            callsign = config["callsign"]

            if not dmr_id or dmr_id == 0:
                raise ValueError(
                    "dmr_id is not set in config.yaml.\n\n"
                    "Register for a DMR ID at https://radioid.net, then add:\n\n"
                    "  dmr_id: 1234567"
                )
            if not callsign or callsign == "N0CALL":
                raise ValueError(
                    "callsign is not set in config.yaml.\n\n"
                    "Add your amateur radio callsign:\n\n"
                    "  callsign: W0ABC"
                )

            post_line(f"Callsign: {callsign}  DMR ID: {dmr_id}")

            strategy = config["organization"]["strategy"]
            post_line(f"Strategy: {strategy}")

            def progress_cb(msg: str, is_cached: bool) -> None:
                post_line(msg, is_err=False)

            api_email = config.get("api_email", "").strip()
            if not api_email:
                raise ValueError(
                    "api_email is not set in config.yaml.\n\n"
                    "RepeaterBook requires a valid contact email in the HTTP User-Agent.\n"
                    "Add this line to your config.yaml:\n\n"
                    "  api_email: you@example.com"
                )

            from plugsmith import __version__
            user_agent = f"plugsmith/{__version__} ({api_email})"
            post_line(f"User-Agent: {user_agent}")

            client = RepeaterBookClient(
                cache_dir=str(Path(config_path).parent / config.get("cache_dir", ".rb_cache")),
                rate_limit=config.get("rate_limit_seconds", 2.0),
                progress_callback=progress_cb,
                user_agent=user_agent,
            )

            all_states = list(US_STATES.keys())
            post_line(f"Fetching {len(all_states)} states…")
            set_status("Fetching repeater data…")
            raw_data = client.fetch_states(all_states)
            post_line(f"Total raw entries: {len(raw_data)}")

            set_status("Parsing…")
            post_line("Parsing repeater data…")
            repeaters = parse_repeaters(raw_data)
            post_line(f"Parsed {len(repeaters)} unique repeaters")

            set_status("Filtering…")
            post_line("Filtering by mode, band, status…")
            repeaters = filter_repeaters(
                repeaters,
                include_fm=config["modes"]["fm"],
                include_dmr=config["modes"]["dmr"],
                include_dstar=config["modes"].get("dstar", False),
                include_fusion=config["modes"].get("fusion", False),
                open_only=config["filters"]["open_only"],
                on_air_only=config["filters"]["on_air_only"],
                bands=config["bands"],
            )
            post_line(f"Filtered to {len(repeaters)} repeaters")

            ref_lat = config["reference_location"]["lat"]
            ref_lon = config["reference_location"]["lon"]
            post_line("Calculating distances…")
            calculate_distances(repeaters, ref_lat, ref_lon)

            home_r = config.get("tiers", {}).get("home_radius_miles", 300)
            adj_r  = config.get("tiers", {}).get("adjacent_radius_miles", 600)
            post_line("Classifying states into tiers…")
            state_tiers = classify_states(repeaters, ref_lat, ref_lon, home_r, adj_r)

            post_line("Building CTCSS and frequency maps…")
            ctcss_map = compute_state_ctcss_map(repeaters)
            input_freq_map = compute_state_input_freq_map(repeaters)

            state_tg_map = dict(STATE_TGS_DEFAULT)
            state_tg_map.update(config.get("state_talkgroups", {}))

            set_status("Organizing zones…")
            post_line("Organizing tiered zones…")
            zone_specs = organize_zones_tiered(
                repeaters, state_tiers, ctcss_map, input_freq_map, config, state_tg_map
            )
            total_ch = sum(len(zs["channels"]) for zs in zone_specs)
            post_line(f"Zones: {len(zone_specs)}, channels: {total_ch}")

            set_status("Generating codeplug YAML…")
            post_line("Generating qdmr YAML…")
            codeplug = generate_codeplug_yaml(
                zone_specs=zone_specs,
                dmr_id=dmr_id,
                callsign=callsign,
                anytone_settings=config.get("anytone_settings"),
            )

            post_line(f"Writing codeplug to {output_path}…")
            write_qdmr_yaml(codeplug, output_path)

            csv_dir = str(Path(output_path).parent / config["output"].get("anytone_csv_dir", "anytone_csv"))
            post_line(f"Writing Anytone CSV to {csv_dir}/…")
            write_anytone_csv(codeplug, csv_dir)

            summary_path = str(Path(output_path).parent / config["output"].get("summary", "codeplug_summary.txt"))
            summary = write_summary(codeplug, summary_path, zone_specs=zone_specs)

            n_ch = len(codeplug["channels"])
            n_zones = len(codeplug["zones"])
            set_status(f"✓ Build complete — {n_ch} channels, {n_zones} zones")
            post_line(f"\n✓ Done: {n_ch} channels, {n_zones} zones written to {output_path}")

            self.call_from_thread(
                self.post_message,
                BuildPane.BuildFinished(success=True, channel_count=n_ch, zone_count=n_zones),
            )

        except Exception as exc:
            import traceback
            tb = traceback.format_exc()
            post_line(f"Build failed: {exc}", is_err=True)
            post_line(tb, is_err=True)
            set_status(f"✗ Build failed: {exc}")
            self.call_from_thread(
                self.post_message,
                BuildPane.BuildFinished(success=False, error=str(exc)),
            )
        finally:
            self.call_from_thread(lambda: setattr(self, "_building", False))
