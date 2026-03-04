"""ConfigEditorPane — edit config.yaml fields in-app."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Button, Collapsible, Input, Label, Select, SelectionList, Static, Switch

from plugsmith.builder.build_config import LOWER_48_STATES
from plugsmith.widgets.field_editors import LabeledInput, LabeledSwitch


_STRATEGY_OPTIONS = [
    ("tiered_region — Home/adjacent/shallow tiers by distance (recommended)", "tiered_region"),
    ("state_band — MO 2m FM, MO 70cm FM per state", "state_band"),
    ("state_county — MO StLouis, MO Franklin per county", "state_county"),
    ("distance_rings — 0-25mi, 25-50mi distance rings", "distance_rings"),
]

_BAND_OPTIONS = [
    ("2m (144–148 MHz)", "2m"),
    ("70cm (420–450 MHz)", "70cm"),
]

_US_STATE_OPTIONS = [
    ("AL", "AL"), ("AK", "AK"), ("AZ", "AZ"), ("AR", "AR"), ("CA", "CA"),
    ("CO", "CO"), ("CT", "CT"), ("DE", "DE"), ("FL", "FL"), ("GA", "GA"),
    ("HI", "HI"), ("ID", "ID"), ("IL", "IL"), ("IN", "IN"), ("IA", "IA"),
    ("KS", "KS"), ("KY", "KY"), ("LA", "LA"), ("ME", "ME"), ("MD", "MD"),
    ("MA", "MA"), ("MI", "MI"), ("MN", "MN"), ("MS", "MS"), ("MO", "MO"),
    ("MT", "MT"), ("NE", "NE"), ("NV", "NV"), ("NH", "NH"), ("NJ", "NJ"),
    ("NM", "NM"), ("NY", "NY"), ("NC", "NC"), ("ND", "ND"), ("OH", "OH"),
    ("OK", "OK"), ("OR", "OR"), ("PA", "PA"), ("RI", "RI"), ("SC", "SC"),
    ("SD", "SD"), ("TN", "TN"), ("TX", "TX"), ("UT", "UT"), ("VT", "VT"),
    ("VA", "VA"), ("WA", "WA"), ("WV", "WV"), ("WI", "WI"), ("WY", "WY"),
]


class ConfigEditorPane(Widget):
    """Tab pane: edit config.yaml fields."""

    DEFAULT_CSS = """
    ConfigEditorPane {
        padding: 1 2;
    }
    ConfigEditorPane ScrollableContainer {
        height: 1fr;
    }
    ConfigEditorPane .section-title {
        color: $primary;
        margin: 1 0 0 0;
        text-style: bold;
    }
    ConfigEditorPane .note {
        color: $text-muted;
        margin: 0 0 1 0;
    }
    ConfigEditorPane .btn-row {
        height: 3;
        margin-top: 1;
    }
    ConfigEditorPane .btn-row Button {
        margin-right: 1;
    }
    """

    _config_path: reactive[str] = reactive("")
    _raw_config: dict = {}

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("[bold]Config Editor[/bold]")
            with Horizontal(classes="row" ):
                yield Label("File: ", id="lbl-config-file")
            with ScrollableContainer():
                # Identity
                yield Label("Identity", classes="section-title")
                yield LabeledInput("DMR ID:", "cfg-dmr-id", placeholder="e.g. 3211477")
                yield LabeledInput("Callsign:", "cfg-callsign", placeholder="e.g. W0RRK")
                yield LabeledInput("Email (API):", "cfg-api-email", placeholder="you@example.com")

                # Location
                yield Label("Location", classes="section-title")
                yield LabeledInput("Latitude:", "cfg-lat", placeholder="e.g. 38.2085")
                yield LabeledInput("Longitude:", "cfg-lon", placeholder="e.g. -91.1604")
                yield LabeledInput("Home State:", "cfg-home-state", placeholder="e.g. MO")

                # Strategy
                yield Label("Zone Strategy", classes="section-title")
                yield Select(
                    options=_STRATEGY_OPTIONS,
                    id="cfg-strategy",
                    prompt="Select strategy…",
                )

                # Tier radii
                yield Label("Coverage Tiers", classes="section-title")
                yield LabeledInput("Home radius (mi):", "cfg-home-radius", placeholder="300")
                yield LabeledInput("Adjacent radius (mi):", "cfg-adj-radius", placeholder="600")

                # States
                yield Label("States to Query", classes="section-title")
                yield Label(
                    "Select which states to fetch from RepeaterBook. Default: lower 48 contiguous states.",
                    classes="note",
                    markup=False,
                )
                yield SelectionList[str](
                    *[(_label, val, val in LOWER_48_STATES) for _label, val in _US_STATE_OPTIONS],
                    id="cfg-states",
                )
                with Horizontal(classes="btn-row"):
                    yield Button("Lower 48", id="btn-states-lower48", variant="default")
                    yield Button("All 50", id="btn-states-all", variant="default")
                    yield Button("Clear", id="btn-states-clear", variant="default")

                # Modes
                yield Label("Modes", classes="section-title")
                yield LabeledSwitch("FM analog:", "cfg-mode-fm", value=True)
                yield LabeledSwitch("DMR digital:", "cfg-mode-dmr", value=True)

                # Filters
                yield Label("Filters", classes="section-title")
                yield LabeledSwitch("Open repeaters only:", "cfg-open-only", value=True)
                yield LabeledSwitch("On-air only:", "cfg-on-air-only", value=True)

                # Bands
                yield Label("Bands", classes="section-title")
                yield SelectionList[str](
                    *[(_label, val, True) for _label, val in _BAND_OPTIONS],
                    id="cfg-bands",
                )

                # Output
                yield Label("Output", classes="section-title")
                yield LabeledInput("qdmr YAML:", "cfg-qdmr-yaml", placeholder="codeplug.yaml")
                yield LabeledInput("Summary file:", "cfg-summary", placeholder="codeplug_summary.txt")
                yield LabeledInput("Cache dir:", "cfg-cache-dir", placeholder=".rb_cache")

                # Advanced (collapsed)
                with Collapsible(title="Advanced", collapsed=True):
                    yield LabeledInput("Rate limit (sec):", "cfg-rate-limit", placeholder="5.0")
                    yield LabeledInput("Home max FM/state:", "cfg-home-max-fm", placeholder="(no cap)")
                    yield LabeledInput("Home max DMR/state:", "cfg-home-max-dmr", placeholder="(no cap)")
                    yield LabeledInput("Adjacent max FM/state:", "cfg-adj-max-fm", placeholder="30")
                    yield LabeledInput("Adjacent max DMR freqs:", "cfg-adj-max-dmr", placeholder="5")
                    yield LabeledInput("Shallow max FM freqs:", "cfg-sha-max-fm", placeholder="10")
                    yield LabeledInput("Shallow max DMR freqs:", "cfg-sha-max-dmr", placeholder="3")

                yield Static(
                    "[dim]Note: [bold]anytone_settings[/bold] is not exposed here — "
                    "edit config.yaml directly for radio hardware settings.[/dim]",
                    classes="note",
                    markup=True,
                )

                with Horizontal(classes="btn-row"):
                    yield Button("Save Config", id="btn-save-config", variant="success")
                    yield Button("Reload from Disk", id="btn-reload-config", variant="default")

    def on_mount(self) -> None:
        from plugsmith.config import load_app_config
        cfg = load_app_config()
        if cfg.codeplug_config:
            self._config_path = cfg.codeplug_config
            self._load_config_file(cfg.codeplug_config)

    def _load_config_file(self, path: str) -> None:
        self._config_path = path
        self.query_one("#lbl-config-file", Label).update(f"File: {path}")
        try:
            with open(path) as f:
                self._raw_config = yaml.safe_load(f) or {}
        except Exception as e:
            from plugsmith.screens.modals import ErrorModal
            self.app.push_screen(ErrorModal("Load Error", str(e)))
            return
        self._populate_fields()

    def _populate_fields(self) -> None:
        cfg = self._raw_config

        def s(val: Any, default: str = "") -> str:
            return str(val) if val is not None else default

        def _set(widget_id: str, val: str) -> None:
            try:
                self.query_one(f"#{widget_id}", LabeledInput).value = val
            except Exception:
                pass

        def _set_sw(widget_id: str, val: bool) -> None:
            try:
                self.query_one(f"#{widget_id}", LabeledSwitch).value = val
            except Exception:
                pass

        _set("cfg-dmr-id", s(cfg.get("dmr_id")))
        _set("cfg-callsign", s(cfg.get("callsign")))
        _set("cfg-api-email", s(cfg.get("api_email")))
        loc = cfg.get("reference_location", {})
        _set("cfg-lat", s(loc.get("lat")))
        _set("cfg-lon", s(loc.get("lon")))
        _set("cfg-home-state", s(cfg.get("home_state")))

        selected = set(cfg.get("states") or LOWER_48_STATES)
        try:
            sl = self.query_one("#cfg-states", SelectionList)
            for _label, val, *_ in _US_STATE_OPTIONS:
                if val in selected:
                    sl.select(val)
                else:
                    sl.deselect(val)
        except Exception:
            pass

        strategy = cfg.get("organization", {}).get("strategy", "tiered_region")
        try:
            self.query_one("#cfg-strategy", Select).value = strategy
        except Exception:
            pass

        tiers = cfg.get("tiers", {})
        _set("cfg-home-radius", s(tiers.get("home_radius_miles")))
        _set("cfg-adj-radius", s(tiers.get("adjacent_radius_miles")))

        modes = cfg.get("modes", {})
        _set_sw("cfg-mode-fm", bool(modes.get("fm", True)))
        _set_sw("cfg-mode-dmr", bool(modes.get("dmr", True)))

        filt = cfg.get("filters", {})
        _set_sw("cfg-open-only", bool(filt.get("open_only", True)))
        _set_sw("cfg-on-air-only", bool(filt.get("on_air_only", True)))

        out = cfg.get("output", {})
        _set("cfg-qdmr-yaml", s(out.get("qdmr_yaml")))
        _set("cfg-summary", s(out.get("summary")))
        _set("cfg-cache-dir", s(cfg.get("cache_dir")))

        _set("cfg-rate-limit", s(cfg.get("rate_limit_seconds")))

        home_r = cfg.get("home_region", {})
        _set("cfg-home-max-fm", s(home_r.get("max_fm_per_state")))
        _set("cfg-home-max-dmr", s(home_r.get("max_dmr_per_state")))

        adj_r = cfg.get("adjacent_region", {})
        _set("cfg-adj-max-fm", s(adj_r.get("max_fm_per_state")))
        _set("cfg-adj-max-dmr", s(adj_r.get("max_dmr_freqs_per_state")))

        sha_r = cfg.get("shallow_region", {})
        _set("cfg-sha-max-fm", s(sha_r.get("max_fm_freqs")))
        _set("cfg-sha-max-dmr", s(sha_r.get("max_dmr_freqs")))

    def _collect_fields(self) -> None:
        """Write form fields back into self._raw_config."""
        cfg = self._raw_config

        def g(widget_id: str) -> str:
            try:
                return self.query_one(f"#{widget_id}", LabeledInput).value.strip()
            except Exception:
                return ""

        def g_sw(widget_id: str) -> bool:
            try:
                return self.query_one(f"#{widget_id}", LabeledSwitch).value
            except Exception:
                return True

        def _set_nested(d: dict, *keys: str, val: Any) -> None:
            for k in keys[:-1]:
                d = d.setdefault(k, {})
            if val not in ("", None):
                d[keys[-1]] = val

        dmr_id_s = g("cfg-dmr-id")
        if dmr_id_s.isdigit():
            cfg["dmr_id"] = int(dmr_id_s)
        cs = g("cfg-callsign")
        if cs:
            cfg["callsign"] = cs
        email = g("cfg-api-email")
        if email:
            cfg["api_email"] = email

        lat_s = g("cfg-lat")
        lon_s = g("cfg-lon")
        try:
            cfg.setdefault("reference_location", {})["lat"] = float(lat_s)
            cfg.setdefault("reference_location", {})["lon"] = float(lon_s)
        except ValueError:
            pass

        hs = g("cfg-home-state")
        if hs:
            cfg["home_state"] = hs.upper()

        try:
            sl = self.query_one("#cfg-states", SelectionList)
            sel = list(sl.selected)
            if sel:
                cfg["states"] = sorted(sel)
        except Exception:
            pass

        strategy = self.query_one("#cfg-strategy", Select).value
        if strategy and strategy != Select.BLANK:
            cfg.setdefault("organization", {})["strategy"] = strategy

        try:
            cfg.setdefault("tiers", {})["home_radius_miles"] = int(g("cfg-home-radius"))
        except ValueError:
            pass
        try:
            cfg.setdefault("tiers", {})["adjacent_radius_miles"] = int(g("cfg-adj-radius"))
        except ValueError:
            pass

        cfg.setdefault("modes", {})["fm"] = g_sw("cfg-mode-fm")
        cfg.setdefault("modes", {})["dmr"] = g_sw("cfg-mode-dmr")
        cfg.setdefault("filters", {})["open_only"] = g_sw("cfg-open-only")
        cfg.setdefault("filters", {})["on_air_only"] = g_sw("cfg-on-air-only")

        qdmr = g("cfg-qdmr-yaml")
        if qdmr:
            cfg.setdefault("output", {})["qdmr_yaml"] = qdmr
        summ = g("cfg-summary")
        if summ:
            cfg.setdefault("output", {})["summary"] = summ
        cd = g("cfg-cache-dir")
        if cd:
            cfg["cache_dir"] = cd

        rl = g("cfg-rate-limit")
        try:
            cfg["rate_limit_seconds"] = float(rl)
        except ValueError:
            pass

        def _opt_int(s: str) -> int | None:
            try:
                return int(s)
            except ValueError:
                return None

        v = _opt_int(g("cfg-home-max-fm"))
        if v is not None:
            cfg.setdefault("home_region", {})["max_fm_per_state"] = v
        v = _opt_int(g("cfg-home-max-dmr"))
        if v is not None:
            cfg.setdefault("home_region", {})["max_dmr_per_state"] = v
        v = _opt_int(g("cfg-adj-max-fm"))
        if v is not None:
            cfg.setdefault("adjacent_region", {})["max_fm_per_state"] = v
        v = _opt_int(g("cfg-adj-max-dmr"))
        if v is not None:
            cfg.setdefault("adjacent_region", {})["max_dmr_freqs_per_state"] = v
        v = _opt_int(g("cfg-sha-max-fm"))
        if v is not None:
            cfg.setdefault("shallow_region", {})["max_fm_freqs"] = v
        v = _opt_int(g("cfg-sha-max-dmr"))
        if v is not None:
            cfg.setdefault("shallow_region", {})["max_dmr_freqs"] = v

    @on(Button.Pressed, "#btn-states-lower48")
    def _states_lower48(self) -> None:
        sl = self.query_one("#cfg-states", SelectionList)
        lower48 = set(LOWER_48_STATES)
        for _label, val, *_ in _US_STATE_OPTIONS:
            if val in lower48:
                sl.select(val)
            else:
                sl.deselect(val)

    @on(Button.Pressed, "#btn-states-all")
    def _states_all(self) -> None:
        self.query_one("#cfg-states", SelectionList).select_all()

    @on(Button.Pressed, "#btn-states-clear")
    def _states_clear(self) -> None:
        self.query_one("#cfg-states", SelectionList).deselect_all()

    @on(Button.Pressed, "#btn-save-config")
    def _save_config(self) -> None:
        if not self._config_path:
            from plugsmith.screens.modals import ErrorModal
            self.app.push_screen(ErrorModal("No Config", "No config file loaded."))
            return
        self._collect_fields()
        try:
            with open(self._config_path, "w") as f:
                yaml.dump(self._raw_config, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
            self.notify(f"Saved: {self._config_path}", severity="information")
        except Exception as e:
            from plugsmith.screens.modals import ErrorModal
            self.app.push_screen(ErrorModal("Save Error", str(e)))

    @on(Button.Pressed, "#btn-reload-config")
    def _reload_config(self) -> None:
        if self._config_path:
            self._load_config_file(self._config_path)

    def set_config_path(self, path: str) -> None:
        """Called externally (e.g. from wizard) to load a config file."""
        self._load_config_file(path)
