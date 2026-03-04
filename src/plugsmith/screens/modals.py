"""Shared modal dialogs: ConfirmModal, ErrorModal, FilePickerModal, WriteAcknowledgeModal."""

from __future__ import annotations

from pathlib import Path

from textual import on
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Checkbox, DirectoryTree, Input, Label, Static


class ConfirmModal(ModalScreen[bool]):
    """A simple yes/no confirmation dialog."""

    DEFAULT_CSS = """
    ConfirmModal {
        align: center middle;
    }
    ConfirmModal Vertical {
        background: $panel;
        border: thick $primary;
        padding: 1 2;
        width: 60;
        height: auto;
    }
    ConfirmModal .message {
        padding: 1 0;
    }
    ConfirmModal Horizontal {
        height: 3;
        align: right middle;
    }
    ConfirmModal Button {
        margin: 0 1;
    }
    """

    def __init__(
        self,
        message: str,
        title: str = "Confirm",
        danger: bool = False,
    ) -> None:
        super().__init__()
        self._message = message
        self._title = title
        self._danger = danger

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(f"[bold]{self._title}[/bold]")
            yield Static(self._message, classes="message")
            with Horizontal():
                yield Button(
                    "Confirm",
                    id="btn-confirm",
                    variant="error" if self._danger else "primary",
                )
                yield Button("Cancel", id="btn-cancel", variant="default")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "btn-confirm")


class ErrorModal(ModalScreen[None]):
    """An error dialog with a Close button."""

    DEFAULT_CSS = """
    ErrorModal {
        align: center middle;
    }
    ErrorModal Vertical {
        background: $panel;
        border: thick $error;
        padding: 1 2;
        width: 70;
        height: auto;
        max-height: 30;
    }
    ErrorModal .title {
        color: $error;
    }
    ErrorModal .message {
        padding: 1 0;
    }
    ErrorModal Button {
        margin-top: 1;
    }
    """

    def __init__(self, title: str = "Error", message: str = "") -> None:
        super().__init__()
        self._title = title
        self._message = message

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(f"[bold]{self._title}[/bold]", classes="title")
            yield Static(self._message, classes="message", markup=True)
            yield Button("Close", id="btn-close", variant="default")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(None)


class FilePickerModal(ModalScreen[Path | None]):
    """A file browser modal. Returns selected Path or None on cancel."""

    DEFAULT_CSS = """
    FilePickerModal {
        align: center middle;
    }
    FilePickerModal Vertical {
        background: $panel;
        border: thick $primary;
        padding: 1 2;
        width: 80;
        height: 30;
    }
    FilePickerModal DirectoryTree {
        height: 1fr;
        border: solid $primary-darken-2;
    }
    FilePickerModal Input {
        margin-top: 1;
    }
    FilePickerModal Horizontal {
        height: 3;
        margin-top: 1;
        align: right middle;
    }
    FilePickerModal Button {
        margin: 0 1;
    }
    """

    def __init__(self, start_path: str = ".", title: str = "Select File") -> None:
        super().__init__()
        self._start_path = start_path
        self._title = title
        self._selected: Path | None = None

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(f"[bold]{self._title}[/bold]")
            yield DirectoryTree(self._start_path, id="dir-tree")
            yield Input(placeholder="Selected path…", id="path-input")
            with Horizontal():
                yield Button("Select", id="btn-select", variant="primary")
                yield Button("Cancel", id="btn-cancel", variant="default")

    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        self._selected = event.path
        self.query_one("#path-input", Input).value = str(event.path)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-select":
            # Try the typed path first, then the tree selection
            typed = self.query_one("#path-input", Input).value.strip()
            if typed:
                p = Path(typed).expanduser()
                if p.exists():
                    self.dismiss(p)
                    return
            if self._selected and self._selected.exists():
                self.dismiss(self._selected)
            else:
                self.dismiss(None)
        else:
            self.dismiss(None)


class WriteAcknowledgeModal(ModalScreen[bool]):
    """Safety gate before writing to radio: warns about experimental status, requires backup confirmation."""

    DEFAULT_CSS = """
    WriteAcknowledgeModal {
        align: center middle;
    }
    WriteAcknowledgeModal Vertical {
        background: $panel;
        border: thick $warning;
        padding: 1 2;
        width: 70;
        height: auto;
    }
    WriteAcknowledgeModal .warning-title {
        color: $warning;
        padding-bottom: 1;
    }
    WriteAcknowledgeModal .body-text {
        padding: 0 0 1 0;
    }
    WriteAcknowledgeModal Checkbox {
        margin-bottom: 1;
    }
    WriteAcknowledgeModal Horizontal {
        height: 3;
        align: right middle;
    }
    WriteAcknowledgeModal Button {
        margin: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("[bold]⚠ Experimental Software Warning[/bold]", classes="warning-title")
            yield Static(
                "plugsmith is experimental software. Writing an incompatible or "
                "incorrect codeplug to your radio could render it inoperable.\n\n"
                "Before proceeding, ensure you have a current backup of your radio "
                "by using [bold]Read .dfu[/bold] or [bold]Read .yaml[/bold] above.",
                classes="body-text",
                markup=True,
            )
            yield Checkbox(
                "I have a backup of my radio and accept the risk",
                id="cb-backup",
                value=False,
            )
            with Horizontal():
                yield Button("Continue", id="btn-continue", variant="warning", disabled=True)
                yield Button("Cancel", id="btn-cancel", variant="default")

    @on(Checkbox.Changed, "#cb-backup")
    def _on_check(self, event: Checkbox.Changed) -> None:
        self.query_one("#btn-continue", Button).disabled = not event.value

    @on(Button.Pressed, "#btn-continue")
    def _confirm(self) -> None:
        self.dismiss(True)

    @on(Button.Pressed, "#btn-cancel")
    def _cancel(self) -> None:
        self.dismiss(False)
