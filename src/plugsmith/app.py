"""PlugsmithApp — root Textual application."""

from __future__ import annotations

from textual.app import App

from plugsmith.config import load_app_config
from plugsmith.screens.main_screen import MainScreen
from plugsmith.screens.setup_wizard import SetupWizardScreen


class PlugsmithApp(App[None]):
    CSS_PATH = "styles/plugsmith.tcss"
    TITLE = "plugsmith"
    SUB_TITLE = "DMR Codeplug Manager"

    def on_mount(self) -> None:
        self.push_screen(MainScreen())
        cfg = load_app_config()
        if not cfg.is_complete():
            self.push_screen(
                SetupWizardScreen(),
                callback=self._on_wizard_complete,
            )

    def _on_wizard_complete(self, completed: bool) -> None:
        if completed:
            # Reload config into main screen
            try:
                from plugsmith.screens.main_screen import MainScreen as MS
                ms = self.query_one(MS)
                ms._refresh_status_bar()
            except Exception:
                pass


def main() -> None:
    """Entry point — launched by `plugsmith` CLI command."""
    PlugsmithApp().run()
