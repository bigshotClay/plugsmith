"""RoamingZoneModal — 3-step modal to add or edit a roaming zone definition."""

from __future__ import annotations

from typing import Optional

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, ContentSwitcher, Input, Label, Static, Switch

from plugsmith.widgets.field_editors import LabeledInput, LabeledSwitch


class RoamingZoneModal(ModalScreen[Optional[dict]]):
    """3-step modal for defining a roaming zone. Returns a zone definition dict or None."""

    DEFAULT_CSS = """
    RoamingZoneModal {
        align: center middle;
    }
    RoamingZoneModal .modal-outer {
        background: $panel;
        border: thick $primary;
        padding: 1 2;
        width: 72;
        height: auto;
    }
    RoamingZoneModal .modal-title {
        margin-bottom: 1;
    }
    RoamingZoneModal .step-title {
        color: $accent;
        margin-bottom: 1;
    }
    RoamingZoneModal .nav-row {
        height: 3;
        align: right middle;
        margin-top: 1;
    }
    RoamingZoneModal .nav-row Button {
        margin-left: 1;
    }
    RoamingZoneModal .summary-text {
        color: $text-muted;
        height: auto;
        margin-top: 1;
    }
    RoamingZoneModal .mode-btn-row {
        height: 5;
        align: center middle;
        margin-top: 1;
        margin-bottom: 1;
    }
    RoamingZoneModal .mode-btn-row Button {
        margin: 0 2;
        width: 28;
        height: 4;
    }
    """

    def __init__(
        self,
        mode: str = "route",
        existing: Optional[dict] = None,
    ) -> None:
        super().__init__()
        self._existing = existing
        self._mode = existing.get("mode", mode) if existing else mode
        # Start at step 1 (locations) since mode is always pre-selected via buttons
        self._initial_step = 1

    def compose(self) -> ComposeResult:
        title = "Edit Roaming Zone" if self._existing else "Add Roaming Zone"
        with Vertical(classes="modal-outer"):
            yield Label(f"[bold]{title}[/bold]", classes="modal-title", markup=True)
            with ContentSwitcher(initial=f"step-{self._initial_step}", id="step-switcher"):

                # Step 0: Mode selection (available but skipped when mode is pre-set)
                with Vertical(id="step-0"):
                    yield Label("Select zone type:", classes="step-title")
                    with Horizontal(classes="mode-btn-row"):
                        yield Button("Route\ntwo cities", id="btn-mode-route", variant="primary")
                        yield Button("Radius\none location", id="btn-mode-radius", variant="default")

                # Step 1: Locations
                with Vertical(id="step-1"):
                    yield Label("Locations:", classes="step-title")
                    with Vertical(id="route-fields"):
                        yield LabeledInput(
                            "From:",
                            "input-from",
                            placeholder="e.g. Chicago, IL  or  41.85,-87.65",
                            value=self._get_existing_from(),
                        )
                        yield LabeledInput(
                            "To:",
                            "input-to",
                            placeholder="e.g. St. Louis, MO  or  38.62,-90.19",
                            value=self._get_existing_to(),
                        )
                        yield LabeledInput(
                            "Corridor (miles):",
                            "input-corridor",
                            placeholder="25",
                            value=str(self._existing.get("corridor_miles", 25)) if self._existing else "25",
                        )
                    with Vertical(id="radius-fields"):
                        yield LabeledInput(
                            "Center:",
                            "input-center",
                            placeholder="e.g. Chicago, IL  or  38.20,-91.16",
                            value=self._existing.get("center", "") if self._existing else "",
                        )
                        yield LabeledInput(
                            "Radius (miles):",
                            "input-radius",
                            placeholder="50",
                            value=str(self._existing.get("radius_miles", 50)) if self._existing else "50",
                        )

                # Step 2: Options
                with Vertical(id="step-2"):
                    yield Label("Options:", classes="step-title")
                    yield LabeledInput(
                        "Zone name:",
                        "input-zone-name",
                        placeholder="e.g. Chicago → St. Louis",
                        value=self._existing.get("name", "") if self._existing else "",
                    )
                    yield LabeledSwitch(
                        "Include FM",
                        "sw-include-fm",
                        value=self._existing.get("include_fm", True) if self._existing else True,
                    )
                    yield LabeledSwitch(
                        "Include DMR",
                        "sw-include-dmr",
                        value=self._existing.get("include_dmr", True) if self._existing else True,
                    )
                    yield Static("", id="step2-summary", classes="summary-text", markup=True)

            with Horizontal(classes="nav-row"):
                yield Button("Back", id="btn-back", variant="default")
                yield Button("Next", id="btn-next", variant="primary")
                yield Button("Save", id="btn-save", variant="success")
                yield Button("Cancel", id="btn-cancel", variant="default")

    def on_mount(self) -> None:
        self._update_mode_visibility()
        self._update_nav_buttons()

    def _get_existing_from(self) -> str:
        if self._existing and self._existing.get("mode") == "route":
            wps = self._existing.get("waypoints", [])
            return wps[0] if wps else ""
        return ""

    def _get_existing_to(self) -> str:
        if self._existing and self._existing.get("mode") == "route":
            wps = self._existing.get("waypoints", [])
            return wps[-1] if len(wps) > 1 else ""
        return ""

    def _current_step(self) -> int:
        try:
            current = self.query_one("#step-switcher", ContentSwitcher).current
            return int(current.split("-")[1])
        except Exception:
            return 1

    def _update_mode_visibility(self) -> None:
        """Show route fields or radius fields based on current mode."""
        is_route = self._mode == "route"
        try:
            self.query_one("#route-fields").display = is_route
            self.query_one("#radius-fields").display = not is_route
        except Exception:
            pass

    def _update_nav_buttons(self) -> None:
        step = self._current_step()
        self.query_one("#btn-back", Button).display = step > 0
        self.query_one("#btn-next", Button).display = step < 2
        self.query_one("#btn-save", Button).display = step == 2

    def _auto_generate_name(self) -> str:
        """Generate a zone name from current location inputs."""
        if self._mode == "route":
            try:
                from_val = self.query_one("#input-from", Input).value.strip()
                to_val = self.query_one("#input-to", Input).value.strip()
                if from_val and to_val:
                    return f"{from_val} → {to_val}"[:64]
            except Exception:
                pass
        else:
            try:
                center_val = self.query_one("#input-center", Input).value.strip()
                radius_val = self.query_one("#input-radius", Input).value.strip() or "50"
                if center_val:
                    return f"{center_val} {radius_val}mi"[:64]
            except Exception:
                pass
        return "Roaming Zone"

    def _update_step2_summary(self) -> None:
        """Refresh the summary block on step 2."""
        try:
            inc_fm = self.query_one("#sw-include-fm", Switch).value
            inc_dmr = self.query_one("#sw-include-dmr", Switch).value
            if self._mode == "route":
                from_v = self.query_one("#input-from", Input).value
                to_v = self.query_one("#input-to", Input).value
                corridor = self.query_one("#input-corridor", Input).value
                lines = [
                    f"[bold]Route:[/bold] {from_v} → {to_v}",
                    f"[bold]Corridor:[/bold] {corridor} miles",
                ]
            else:
                center = self.query_one("#input-center", Input).value
                radius = self.query_one("#input-radius", Input).value
                lines = [
                    f"[bold]Center:[/bold] {center}",
                    f"[bold]Radius:[/bold] {radius} miles",
                ]
            fm_str = "✓" if inc_fm else "✗"
            dmr_str = "✓" if inc_dmr else "✗"
            lines.append(f"[bold]FM:[/bold] {fm_str}  [bold]DMR:[/bold] {dmr_str}")
            self.query_one("#step2-summary", Static).update("\n".join(lines))
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id

        if btn_id == "btn-cancel":
            self.dismiss(None)

        elif btn_id == "btn-mode-route":
            self._mode = "route"
            self.query_one("#step-switcher", ContentSwitcher).current = "step-1"
            self._update_mode_visibility()
            self._update_nav_buttons()

        elif btn_id == "btn-mode-radius":
            self._mode = "radius"
            self.query_one("#step-switcher", ContentSwitcher).current = "step-1"
            self._update_mode_visibility()
            self._update_nav_buttons()

        elif btn_id == "btn-next":
            current = self._current_step()
            if current < 2:
                if current == 1:
                    # Auto-populate name if blank before advancing to step 2
                    name_input = self.query_one("#input-zone-name", Input)
                    if not name_input.value.strip():
                        name_input.value = self._auto_generate_name()
                    self._update_step2_summary()
                self.query_one("#step-switcher", ContentSwitcher).current = f"step-{current + 1}"
                self._update_nav_buttons()

        elif btn_id == "btn-back":
            current = self._current_step()
            if current > 0:
                self.query_one("#step-switcher", ContentSwitcher).current = f"step-{current - 1}"
                self._update_nav_buttons()

        elif btn_id == "btn-save":
            defn = self._collect_definition()
            if defn is not None:
                self.dismiss(defn)

    def _collect_definition(self) -> Optional[dict]:
        """Build and validate the zone definition dict from current inputs."""
        try:
            name = self.query_one("#input-zone-name", Input).value.strip()
            if not name:
                name = self._auto_generate_name()
            inc_fm = self.query_one("#sw-include-fm", Switch).value
            inc_dmr = self.query_one("#sw-include-dmr", Switch).value

            if self._mode == "route":
                from_val = self.query_one("#input-from", Input).value.strip()
                to_val = self.query_one("#input-to", Input).value.strip()
                if not from_val or not to_val:
                    return None
                try:
                    corridor = float(self.query_one("#input-corridor", Input).value.strip() or "25")
                except ValueError:
                    corridor = 25.0
                return {
                    "name": name,
                    "mode": "route",
                    "waypoints": [from_val, to_val],
                    "corridor_miles": corridor,
                    "include_fm": inc_fm,
                    "include_dmr": inc_dmr,
                }
            else:
                center = self.query_one("#input-center", Input).value.strip()
                if not center:
                    return None
                try:
                    radius = float(self.query_one("#input-radius", Input).value.strip() or "50")
                except ValueError:
                    radius = 50.0
                return {
                    "name": name,
                    "mode": "radius",
                    "center": center,
                    "radius_miles": radius,
                    "include_fm": inc_fm,
                    "include_dmr": inc_dmr,
                }
        except Exception:
            return None
