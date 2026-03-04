"""ConfigEditorPane — edit config.yaml fields in-app."""

from __future__ import annotations

from typing import Any

import yaml
from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Button, Collapsible, Input, Label, Select, SelectionList, Static, Switch

from plugsmith.builder.build_config import LOWER_48_STATES
from plugsmith.builder.radio_settings_meta import ANYTONE_SETTINGS, SettingMeta
from plugsmith.screens.generic_hw_settings import GenericHwPane
from plugsmith.widgets.field_editors import LabeledInput, LabeledSwitch


# ---------------------------------------------------------------------------
# Module-level helpers for AnyTone hardware rendering
# ---------------------------------------------------------------------------

def _hw_widget_id(group_key: str, field_key: str) -> str:
    return f"hw-{group_key}-{field_key}"


def _compose_hw_entry(group_key: str, meta: SettingMeta) -> ComposeResult:
    """Yield widgets for one AnyTone hardware setting row."""
    widget_id = _hw_widget_id(group_key, meta.key)
    with Vertical(classes="hw-entry"):
        with Horizontal(classes="hw-row"):
            yield Label(meta.label, classes="hw-label")
            if meta.stype == "bool":
                yield Switch(value=bool(meta.default), id=widget_id, classes="hw-control")
            elif meta.stype == "enum" and meta.options:
                opts = [(v, v) for v in meta.options]
                yield Select(
                    options=opts,
                    value=str(meta.default) if meta.default is not None else Select.BLANK,
                    id=widget_id,
                    classes="hw-control",
                )
            else:
                yield Input(
                    value=str(meta.default) if meta.default is not None else "",
                    id=widget_id,
                    classes="hw-control",
                )
        yield Static(meta.description, classes="hw-desc", markup=False)
        yield Static(f"Ham preferred: {meta.ham_preferred}", classes="hw-preferred", markup=False)
        if meta.warning:
            yield Static(f"\u26a0 {meta.warning}", classes="hw-warning", markup=False)


class _AnyToneHwSection(Widget):
    """AnyTone hardware settings form — renders metadata-driven controls via compose()."""

    DEFAULT_CSS = ""

    def compose(self) -> ComposeResult:
        yield Static(
            "[dim]These settings are written to the [bold]anytone_settings[/bold] block "
            "in config.yaml and apply to AT-D868UV, AT-D878UV, AT-D878UVII, and AT-D578UV. "
            "They control radio behavior, display, audio, and DMR parameters.[/dim]",
            classes="note",
            markup=True,
        )
        for display_name, group_key, settings in ANYTONE_SETTINGS:
            with Collapsible(title=display_name, collapsed=True):
                for meta in settings:
                    yield from _compose_hw_entry(group_key, meta)


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
    ConfigEditorPane .simplex-row {
        height: 3;
        margin-bottom: 1;
        align: left middle;
    }
    ConfigEditorPane .simplex-row Input {
        width: 1fr;
        margin-right: 1;
    }
    ConfigEditorPane .simplex-row Button {
        width: 5;
    }
    ConfigEditorPane .state-tg-row {
        height: 3;
        margin-bottom: 1;
        align: left middle;
    }
    ConfigEditorPane .state-tg-row Select {
        width: 1fr;
        margin-right: 1;
    }
    ConfigEditorPane .state-tg-row Input {
        width: 12;
        margin-right: 1;
    }
    ConfigEditorPane .state-tg-row Button {
        width: 5;
    }

    /* Hardware setting entry rows */
    ConfigEditorPane .hw-entry {
        margin: 0 0 1 0;
        padding: 0 0 0 1;
        border-left: tall $primary-background-darken-2;
    }
    ConfigEditorPane .hw-row {
        height: 3;
        align: left middle;
    }
    ConfigEditorPane .hw-label {
        width: 30;
        padding: 1 1 1 0;
        color: $text;
        text-style: bold;
    }
    ConfigEditorPane .hw-control {
        width: 1fr;
    }
    ConfigEditorPane .hw-desc {
        color: $text-muted;
        padding: 0 0 0 0;
        margin: 0 0 0 0;
    }
    ConfigEditorPane .hw-preferred {
        color: $success;
        padding: 0 0 0 0;
        margin: 0 0 0 0;
    }
    ConfigEditorPane .hw-warning {
        color: $warning;
        text-style: bold;
        padding: 0 0 0 0;
        margin: 0 0 0 0;
    }
    ConfigEditorPane #hw-no-settings-notice {
        color: $text-muted;
        margin: 1 0;
        padding: 0 1;
    }
    """

    _config_path: reactive[str] = reactive("")
    _raw_config: dict = {}
    _hw_mode: str = ""  # "anytone" | "generic" | "none"
    _generic_settings_key: str = ""
    _simplex_counter: int = 0
    _state_tg_counter: int = 0

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

                # Talkgroup Settings
                yield Label("Talkgroup Settings", classes="section-title")
                yield Label("Networks to fetch talkgroup data from:", classes="note", markup=False)
                yield SelectionList[str](
                    ("BrandMeister", "brandmeister", True),
                    ("TGIF", "tgif", True),
                    id="cfg-tg-networks",
                )
                yield LabeledSwitch("Fill contact list:", "cfg-tg-fill-contacts", value=True)
                yield LabeledSwitch("Per-repeater RadioID lookup:", "cfg-tg-per-repeater", value=True)

                # Simplex Channels
                yield Label("Simplex Channels", classes="section-title")
                yield Label(
                    "Predefined simplex/calling channels added to every codeplug.",
                    classes="note",
                    markup=False,
                )
                yield Vertical(id="simplex-rows")
                yield Button("+ Add Channel", id="btn-add-simplex", variant="default")

                # State Talkgroup Overrides
                yield Label("State Talkgroup Overrides", classes="section-title")
                yield Label(
                    "Override the default BrandMeister state TG ID for a specific state. "
                    "Leave empty to use built-in defaults.",
                    classes="note",
                    markup=False,
                )
                yield Vertical(id="state-tg-rows")
                yield Button("+ Add Override", id="btn-add-state-tg", variant="default")

                # Output
                yield Label("Output", classes="section-title")
                yield LabeledInput("qdmr YAML:", "cfg-qdmr-yaml", placeholder="codeplug.yaml")
                yield LabeledInput("Anytone CSV dir:", "cfg-csv-dir", placeholder="anytone_csv")
                yield LabeledInput("Summary file:", "cfg-summary", placeholder="codeplug_summary.txt")
                yield LabeledInput("Cache dir:", "cfg-cache-dir", placeholder=".rb_cache")

                # Advanced (collapsed)
                with Collapsible(title="Advanced", collapsed=True):
                    yield LabeledInput("Rate limit (sec):", "cfg-rate-limit", placeholder="5.0")
                    yield LabeledInput("Home max FM/state:", "cfg-home-max-fm", placeholder="(no cap)")
                    yield LabeledInput("Home max DMR/state:", "cfg-home-max-dmr", placeholder="(no cap)")
                    yield LabeledInput("Home TGs/repeater:", "cfg-home-tgs-per-rep", placeholder="7")
                    yield LabeledInput("Adjacent max FM/state:", "cfg-adj-max-fm", placeholder="30")
                    yield LabeledInput("Adjacent max DMR freqs:", "cfg-adj-max-dmr", placeholder="5")
                    yield LabeledInput("Adj TGs/freq:", "cfg-adj-tgs-per-freq", placeholder="3")
                    yield LabeledInput("Shallow max FM freqs:", "cfg-sha-max-fm", placeholder="10")
                    yield LabeledInput("Shallow max DMR freqs:", "cfg-sha-max-dmr", placeholder="3")

                # Hardware settings — dynamically populated after load
                yield Vertical(id="hw-section-outer")

                with Horizontal(classes="btn-row"):
                    yield Button("Save Config", id="btn-save-config", variant="success")
                    yield Button("Reload from Disk", id="btn-reload-config", variant="default")

    # ------------------------------------------------------------------
    # Simplex channel helpers
    # ------------------------------------------------------------------

    def _add_simplex_row(self, name: str = "", freq: str = "") -> None:
        self._simplex_counter += 1
        n = self._simplex_counter
        try:
            self.query_one("#simplex-rows", Vertical).mount(
                Horizontal(
                    Input(value=name, placeholder="Name", id=f"simplex-name-{n}"),
                    Input(value=freq, placeholder="Freq (MHz)", id=f"simplex-freq-{n}"),
                    Button("✕", id=f"simplex-del-{n}", variant="error"),
                    classes="simplex-row",
                    id=f"simplex-row-{n}",
                )
            )
        except Exception:
            pass

    def _populate_simplex(self) -> None:
        channels = list(self._raw_config.get("simplex", {}).get("channels", []))

        def _do_mount() -> None:
            try:
                container = self.query_one("#simplex-rows", Vertical)
                container.remove_children()
                self._simplex_counter = 0
                for ch in channels:
                    self._add_simplex_row(
                        name=str(ch.get("name", "")),
                        freq=str(ch.get("freq", "")),
                    )
            except Exception:
                pass

        self.call_after_refresh(_do_mount)

    def _collect_simplex(self) -> None:
        channels = []
        for n in range(1, self._simplex_counter + 1):
            try:
                name = self.query_one(f"#simplex-name-{n}", Input).value.strip()
                freq_s = self.query_one(f"#simplex-freq-{n}", Input).value.strip()
            except Exception:
                continue  # row was deleted
            if name or freq_s:
                try:
                    freq_v: float | str = float(freq_s)
                except ValueError:
                    freq_v = freq_s
                channels.append({"name": name, "freq": freq_v})
        if channels:
            self._raw_config.setdefault("simplex", {})["channels"] = channels
        elif "simplex" in self._raw_config:
            self._raw_config["simplex"].pop("channels", None)

    @on(Button.Pressed, "#btn-add-simplex")
    def _add_simplex(self) -> None:
        self._add_simplex_row()

    # ------------------------------------------------------------------
    # State talkgroup override helpers
    # ------------------------------------------------------------------

    def _add_state_tg_row(self, state: str = "", tg_id: str = "") -> None:
        self._state_tg_counter += 1
        n = self._state_tg_counter
        try:
            self.query_one("#state-tg-rows", Vertical).mount(
                Horizontal(
                    Select(
                        options=_US_STATE_OPTIONS,
                        value=state if state else Select.BLANK,
                        id=f"state-tg-state-{n}",
                        prompt="State…",
                    ),
                    Input(value=tg_id, placeholder="TG ID", id=f"state-tg-id-{n}"),
                    Button("✕", id=f"state-tg-del-{n}", variant="error"),
                    classes="state-tg-row",
                    id=f"state-tg-row-{n}",
                )
            )
        except Exception:
            pass

    def _populate_state_tgs(self) -> None:
        overrides = dict(self._raw_config.get("state_talkgroups", {}))

        def _do_mount() -> None:
            try:
                container = self.query_one("#state-tg-rows", Vertical)
                container.remove_children()
                self._state_tg_counter = 0
                for state, tg_id in overrides.items():
                    self._add_state_tg_row(state=str(state), tg_id=str(tg_id))
            except Exception:
                pass

        self.call_after_refresh(_do_mount)

    def _collect_state_tgs(self) -> None:
        overrides: dict[str, int] = {}
        for i in range(1, self._state_tg_counter + 1):
            try:
                state_val = self.query_one(f"#state-tg-state-{i}", Select).value
                tg_id_s = self.query_one(f"#state-tg-id-{i}", Input).value.strip()
            except Exception:
                continue
            if state_val and state_val != Select.BLANK and tg_id_s.isdigit():
                overrides[str(state_val)] = int(tg_id_s)
        if overrides:
            self._raw_config["state_talkgroups"] = overrides
        elif "state_talkgroups" in self._raw_config:
            del self._raw_config["state_talkgroups"]

    @on(Button.Pressed, "#btn-add-state-tg")
    def _add_state_tg(self) -> None:
        self._add_state_tg_row()

    @on(Button.Pressed)
    def _maybe_del_row(self, event: Button.Pressed) -> None:
        """Handle delete buttons for both simplex and state-tg dynamic rows."""
        btn_id = event.button.id or ""
        if btn_id.startswith("simplex-del-"):
            n = btn_id.removeprefix("simplex-del-")
            try:
                self.query_one(f"#simplex-row-{n}").remove()
            except Exception:
                pass
            event.stop()
        elif btn_id.startswith("state-tg-del-"):
            n = btn_id.removeprefix("state-tg-del-")
            try:
                self.query_one(f"#state-tg-row-{n}").remove()
            except Exception:
                pass
            event.stop()

    # ------------------------------------------------------------------
    # Hardware settings helpers
    # ------------------------------------------------------------------

    def _refresh_hw_section(self) -> None:
        """Mount the appropriate hw section based on the configured radio model."""
        from plugsmith.config import load_app_config
        from plugsmith.tool_discovery import RADIO_PROFILES

        cfg = load_app_config()
        profile = RADIO_PROFILES.get(cfg.radio_model or "")
        outer = self.query_one("#hw-section-outer", Vertical)
        outer.remove_children()

        if profile and profile.hw_settings_key:
            # AnyTone: mount metadata-driven collapsible
            self._hw_mode = "anytone"
            outer.mount(Collapsible(
                _AnyToneHwSection(),
                title="Radio Hardware Settings (AnyTone)",
                collapsed=True,
                id="hw-anytone-collapsible",
            ))
            self.call_after_refresh(self._populate_hw_fields)
        else:
            model_key = cfg.radio_model or "device"
            settings_key = f"{model_key}_settings"
            data = self._raw_config.get(settings_key, {})
            self._generic_settings_key = settings_key

            if data:
                self._hw_mode = "generic"
                outer.mount(Collapsible(
                    GenericHwPane(settings_key, data, id="hw-generic-pane"),
                    title=f"Radio Hardware Settings ({cfg.radio_model or 'Generic'})",
                    collapsed=False,
                    id="hw-generic-collapsible",
                ))
            else:
                self._hw_mode = "none"
                outer.mount(Static(
                    f"No device-specific settings found for [bold]{cfg.radio_model or 'this radio'}[/bold]. "
                    f"Add a [bold]{settings_key}[/bold] block to your config.yaml, "
                    f"or import settings from a codeplug YAML.",
                    id="hw-no-settings-notice",
                    markup=True,
                ))
                outer.mount(Button("Import Settings from YAML\u2026", id="btn-import-hw-yaml", variant="default"))

    def _populate_hw_fields(self) -> None:
        """Load anytone_settings from _raw_config into hw widgets."""
        hw_block = self._raw_config.get("anytone_settings", {})
        for _, group_key, settings in ANYTONE_SETTINGS:
            group = hw_block.get(group_key, {})
            for meta in settings:
                widget_id = _hw_widget_id(group_key, meta.key)
                raw_val = group.get(meta.key, meta.default)
                try:
                    if meta.stype == "bool":
                        self.query_one(f"#{widget_id}", Switch).value = bool(raw_val)
                    elif meta.stype == "enum":
                        sel = self.query_one(f"#{widget_id}", Select)
                        sel.value = str(raw_val) if raw_val is not None else Select.BLANK
                    else:
                        self.query_one(f"#{widget_id}", Input).value = (
                            str(raw_val) if raw_val is not None else ""
                        )
                except Exception:
                    pass

    def _collect_hw_fields(self) -> None:
        """Write hw widget values back into _raw_config."""
        if self._hw_mode == "anytone":
            hw_block = self._raw_config.setdefault("anytone_settings", {})
            for _, group_key, settings in ANYTONE_SETTINGS:
                group = hw_block.setdefault(group_key, {})
                for meta in settings:
                    widget_id = _hw_widget_id(group_key, meta.key)
                    try:
                        if meta.stype == "bool":
                            group[meta.key] = self.query_one(f"#{widget_id}", Switch).value
                        elif meta.stype == "enum":
                            val = self.query_one(f"#{widget_id}", Select).value
                            if val and val != Select.BLANK:
                                group[meta.key] = val
                        elif meta.stype == "int":
                            raw = self.query_one(f"#{widget_id}", Input).value.strip()
                            try:
                                group[meta.key] = int(raw)
                            except ValueError:
                                pass
                        else:
                            raw = self.query_one(f"#{widget_id}", Input).value.strip()
                            if raw:
                                group[meta.key] = raw
                    except Exception:
                        pass
        elif self._hw_mode == "generic":
            try:
                pane = self.query_one("#hw-generic-pane", GenericHwPane)
                self._raw_config[self._generic_settings_key] = pane.collect()
            except Exception:
                pass

    # ------------------------------------------------------------------

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
        self._refresh_hw_section()
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
        _set("cfg-csv-dir", s(out.get("anytone_csv_dir")))
        _set("cfg-summary", s(out.get("summary")))
        _set("cfg-cache-dir", s(cfg.get("cache_dir")))

        # Talkgroup settings
        tg = cfg.get("talkgroups", {})
        networks = tg.get("networks", ["brandmeister", "tgif"])
        try:
            sl_tg = self.query_one("#cfg-tg-networks", SelectionList)
            for net in ("brandmeister", "tgif"):
                if net in networks:
                    sl_tg.select(net)
                else:
                    sl_tg.deselect(net)
        except Exception:
            pass
        _set_sw("cfg-tg-fill-contacts", bool(tg.get("fill_contacts", True)))
        _set_sw("cfg-tg-per-repeater", bool(tg.get("per_repeater_lookup", True)))

        self._populate_simplex()
        self._populate_state_tgs()

        _set("cfg-rate-limit", s(cfg.get("rate_limit_seconds")))

        home_r = cfg.get("home_region", {})
        _set("cfg-home-max-fm", s(home_r.get("max_fm_per_state")))
        _set("cfg-home-max-dmr", s(home_r.get("max_dmr_per_state")))
        _set("cfg-home-tgs-per-rep", s(home_r.get("dmr_talkgroups_per_repeater")))

        adj_r = cfg.get("adjacent_region", {})
        _set("cfg-adj-max-fm", s(adj_r.get("max_fm_per_state")))
        _set("cfg-adj-max-dmr", s(adj_r.get("max_dmr_freqs_per_state")))
        _set("cfg-adj-tgs-per-freq", s(adj_r.get("dmr_tgs_per_freq")))

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
        csv_dir = g("cfg-csv-dir")
        if csv_dir:
            cfg.setdefault("output", {})["anytone_csv_dir"] = csv_dir
        summ = g("cfg-summary")
        if summ:
            cfg.setdefault("output", {})["summary"] = summ
        cd = g("cfg-cache-dir")
        if cd:
            cfg["cache_dir"] = cd

        # Talkgroup settings
        try:
            sl_tg = self.query_one("#cfg-tg-networks", SelectionList)
            cfg.setdefault("talkgroups", {})["networks"] = list(sl_tg.selected)
        except Exception:
            pass
        cfg.setdefault("talkgroups", {})["fill_contacts"] = g_sw("cfg-tg-fill-contacts")
        cfg.setdefault("talkgroups", {})["per_repeater_lookup"] = g_sw("cfg-tg-per-repeater")

        self._collect_simplex()
        self._collect_state_tgs()

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
        v = _opt_int(g("cfg-home-tgs-per-rep"))
        if v is not None:
            cfg.setdefault("home_region", {})["dmr_talkgroups_per_repeater"] = v
        v = _opt_int(g("cfg-adj-max-fm"))
        if v is not None:
            cfg.setdefault("adjacent_region", {})["max_fm_per_state"] = v
        v = _opt_int(g("cfg-adj-max-dmr"))
        if v is not None:
            cfg.setdefault("adjacent_region", {})["max_dmr_freqs_per_state"] = v
        v = _opt_int(g("cfg-adj-tgs-per-freq"))
        if v is not None:
            cfg.setdefault("adjacent_region", {})["dmr_tgs_per_freq"] = v
        v = _opt_int(g("cfg-sha-max-fm"))
        if v is not None:
            cfg.setdefault("shallow_region", {})["max_fm_freqs"] = v
        v = _opt_int(g("cfg-sha-max-dmr"))
        if v is not None:
            cfg.setdefault("shallow_region", {})["max_dmr_freqs"] = v

        self._collect_hw_fields()

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

    @on(Button.Pressed, "#btn-import-hw-yaml")
    def _import_hw_yaml(self) -> None:
        from plugsmith.screens.modals import FilePickerModal, ErrorModal

        def on_selected(path: object) -> None:
            if not path:
                return
            try:
                with open(str(path)) as f:
                    data = yaml.safe_load(f) or {}
                self._raw_config[self._generic_settings_key] = data
                self._refresh_hw_section()
                self.notify(f"Imported settings from {path}", severity="information")
            except Exception as e:
                self.app.push_screen(ErrorModal("Import Error", str(e)))

        self.app.push_screen(FilePickerModal(), on_selected)

    def set_config_path(self, path: str) -> None:
        """Called externally (e.g. from wizard) to load a config file."""
        self._load_config_file(path)
