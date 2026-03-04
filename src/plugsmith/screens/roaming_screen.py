"""RoamingPane — Roaming Zones tab (list, add, edit, delete)."""

from __future__ import annotations

from typing import Optional

import yaml

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widget import Widget
from textual.widgets import Button, DataTable, Label, Static


class RoamingPane(Widget):
    """Displays saved roaming zone definitions and allows add/edit/delete."""

    DEFAULT_CSS = """
    RoamingPane {
        padding: 1 2;
    }
    RoamingPane .pane-header {
        height: 2;
        margin-bottom: 1;
    }
    RoamingPane .config-dim {
        color: $text-muted;
        margin-left: 1;
    }
    RoamingPane DataTable {
        height: 1fr;
        margin-bottom: 1;
    }
    RoamingPane .btn-row {
        height: 3;
        margin-bottom: 1;
    }
    RoamingPane .btn-row Button {
        margin-right: 1;
    }
    RoamingPane .info-text {
        color: $text-muted;
        height: auto;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical():
            with Horizontal(classes="pane-header"):
                yield Label("[bold]Roaming Zones[/bold]", markup=True)
                yield Label("", id="roaming-config-label", classes="config-dim")
            yield DataTable(id="roaming-table")
            with Horizontal(classes="btn-row"):
                yield Button("Add Route", id="btn-add-route", variant="primary")
                yield Button("Add Radius Zone", id="btn-add-radius", variant="primary")
                yield Button("Edit", id="btn-edit", disabled=True, variant="default")
                yield Button("Delete", id="btn-delete", disabled=True, variant="error")
            yield Static(
                "Changes are saved to config.yaml and applied on next build. "
                "States along the route must be in your cache.",
                classes="info-text",
            )

    def on_mount(self) -> None:
        table = self.query_one("#roaming-table", DataTable)
        table.add_columns("Name", "Mode", "Location(s)", "Distance", "FM", "DMR")
        self._reload_table()

    def _config_path(self) -> Optional[str]:
        from plugsmith.config import load_app_config
        cfg = load_app_config()
        return cfg.codeplug_config or None

    def _reload_table(self) -> None:
        from plugsmith.config import load_app_config
        cfg = load_app_config()
        config_path = cfg.codeplug_config

        if config_path:
            self.query_one("#roaming-config-label", Label).update(
                f"Config: {config_path}"
            )

        table = self.query_one("#roaming-table", DataTable)
        table.clear()

        defs = self._load_roaming_defs()
        for defn in defs:
            name = defn.get("name", "")
            mode = defn.get("mode", "radius")
            if mode == "route":
                wps = defn.get("waypoints", [])
                location = " → ".join(wps) if wps else ""
                distance = f"{defn.get('corridor_miles', 25)}mi corridor"
            else:
                location = defn.get("center", "")
                distance = f"{defn.get('radius_miles', 50)}mi radius"
            fm = "✓" if defn.get("include_fm", True) else "—"
            dmr = "✓" if defn.get("include_dmr", True) else "—"
            table.add_row(name, mode, location, distance, fm, dmr)

    def _load_roaming_defs(self) -> list[dict]:
        config_path = self._config_path()
        if not config_path:
            return []
        try:
            with open(config_path) as f:
                cfg = yaml.safe_load(f) or {}
            return cfg.get("roaming_zones", [])
        except Exception:
            return []

    def _save_roaming_defs(self, defs: list[dict]) -> None:
        config_path = self._config_path()
        if not config_path:
            return
        try:
            with open(config_path) as f:
                cfg = yaml.safe_load(f) or {}
            cfg["roaming_zones"] = defs
            with open(config_path, "w") as f:
                yaml.dump(cfg, f, default_flow_style=False, sort_keys=False)
        except Exception as exc:
            from plugsmith.screens.modals import ErrorModal
            self.app.push_screen(ErrorModal("Save Failed", str(exc)))

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        has_sel = event.row_key is not None
        self.query_one("#btn-edit", Button).disabled = not has_sel
        self.query_one("#btn-delete", Button).disabled = not has_sel

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id

        if btn_id == "btn-add-route":
            from plugsmith.screens.roaming_zone_modal import RoamingZoneModal
            self.app.push_screen(
                RoamingZoneModal(mode="route"),
                callback=self._on_zone_saved,
            )
        elif btn_id == "btn-add-radius":
            from plugsmith.screens.roaming_zone_modal import RoamingZoneModal
            self.app.push_screen(
                RoamingZoneModal(mode="radius"),
                callback=self._on_zone_saved,
            )
        elif btn_id == "btn-edit":
            table = self.query_one("#roaming-table", DataTable)
            row_idx = table.cursor_row
            defs = self._load_roaming_defs()
            if 0 <= row_idx < len(defs):
                from plugsmith.screens.roaming_zone_modal import RoamingZoneModal
                existing = defs[row_idx]
                self.app.push_screen(
                    RoamingZoneModal(existing=existing),
                    callback=lambda defn: self._on_zone_edited(defn, row_idx),
                )
        elif btn_id == "btn-delete":
            table = self.query_one("#roaming-table", DataTable)
            row_idx = table.cursor_row
            defs = self._load_roaming_defs()
            if 0 <= row_idx < len(defs):
                name = defs[row_idx].get("name", "this zone")
                from plugsmith.screens.modals import ConfirmModal
                self.app.push_screen(
                    ConfirmModal(f"Delete zone '{name}'?", title="Delete Zone"),
                    callback=lambda confirmed: self._on_delete_confirmed(confirmed, row_idx),
                )

    def _on_zone_saved(self, defn: dict | None) -> None:
        if defn is not None:
            defs = self._load_roaming_defs()
            defs.append(defn)
            self._save_roaming_defs(defs)
            self._reload_table()

    def _on_zone_edited(self, defn: dict | None, row_idx: int) -> None:
        if defn is not None:
            defs = self._load_roaming_defs()
            if 0 <= row_idx < len(defs):
                defs[row_idx] = defn
                self._save_roaming_defs(defs)
                self._reload_table()

    def _on_delete_confirmed(self, confirmed: bool, row_idx: int) -> None:
        if confirmed:
            defs = self._load_roaming_defs()
            if 0 <= row_idx < len(defs):
                defs.pop(row_idx)
                self._save_roaming_defs(defs)
                self._reload_table()
            self.query_one("#btn-edit", Button).disabled = True
            self.query_one("#btn-delete", Button).disabled = True
