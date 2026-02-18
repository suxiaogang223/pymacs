"""Textual TUI application for PyMACS."""

from __future__ import annotations

from rich.text import Text
from textual.app import App, ComposeResult
from textual.events import Key
from textual.widgets import Input, Static

from ..commands import register_builtin_commands
from ..core import Editor
from .controller import UIController


def _key_to_sequence(key: str) -> str | None:
    parts = key.lower().split("+")
    mods: list[str] = []
    base = ""
    for part in parts:
        if part == "ctrl":
            mods.append("C")
        elif part == "alt":
            mods.append("M")
        elif part == "shift":
            mods.append("S")
        else:
            base = part
    if not base or not mods:
        return None
    return "-".join([*mods, base])


class BufferView(Static):
    can_focus = True


class PyMACSTuiApp(App[None]):
    """Core M4 Textual prototype."""

    CSS = """
    Screen {
        layout: vertical;
    }

    #buffer {
        height: 1fr;
        border: round $accent;
        padding: 1 2;
    }

    #status {
        height: 1;
        padding: 0 1;
        background: $panel;
        color: $text;
    }

    #minibuffer {
        height: 3;
        margin: 0 1 1 1;
    }
    """

    def __init__(self, editor: Editor | None = None) -> None:
        super().__init__()
        self.editor = editor or Editor()
        register_builtin_commands(self.editor)
        self.controller = UIController(self.editor)
        self._quit_requested = False

        self.editor.command("ui-quit", self._cmd_quit)
        self.editor.command("ui-command-focus", self._cmd_focus_minibuffer)
        self.editor.command("ui-command-cancel", self._cmd_cancel_minibuffer)
        self.editor.bind_key("C-q", "ui-quit")
        self.editor.bind_key("M-x", "ui-command-focus")
        self.editor.bind_key("C-g", "ui-command-cancel")

    @property
    def quit_requested(self) -> bool:
        return self._quit_requested

    def compose(self) -> ComposeResult:
        yield BufferView(id="buffer")
        yield Static(id="status")
        yield Input(placeholder="M-x command", id="minibuffer")

    def on_mount(self) -> None:
        self._hide_minibuffer()
        self.query_one("#buffer", BufferView).focus()
        self._refresh_view()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "minibuffer":
            return
        self.controller.execute_minibuffer(event.value)
        self._hide_minibuffer()
        self._refresh_view()

    def on_key(self, event: Key) -> None:
        minibuffer = self.query_one("#minibuffer", Input)
        if minibuffer.display:
            if event.key in {"escape", "ctrl+g"}:
                self.controller.execute_key("C-g")
                self._refresh_view()
                event.stop()
            return

        if event.key == "enter":
            self.controller.handle_text_input("\n")
            self._refresh_view()
            event.stop()
            return

        if event.key == "backspace":
            self.controller.handle_backspace()
            self._refresh_view()
            event.stop()
            return

        sequence = _key_to_sequence(event.key)
        if sequence is not None:
            self.controller.execute_key(sequence)
            self._refresh_view()
            event.stop()
            return

        if event.character and event.character.isprintable():
            self.controller.handle_text_input(event.character)
            self._refresh_view()
            event.stop()

    def _cmd_quit(self, _editor: Editor) -> None:
        self._quit_requested = True
        self.exit()

    def _cmd_focus_minibuffer(self, _editor: Editor) -> None:
        minibuffer = self.query_one("#minibuffer", Input)
        minibuffer.display = True
        minibuffer.value = ""
        minibuffer.focus()

    def _cmd_cancel_minibuffer(self, _editor: Editor) -> None:
        self._hide_minibuffer()

    def _hide_minibuffer(self) -> None:
        minibuffer = self.query_one("#minibuffer", Input)
        minibuffer.value = ""
        minibuffer.display = False
        self.query_one("#buffer", BufferView).focus()

    def _refresh_view(self) -> None:
        snapshot = self.controller.snapshot()
        buffer_widget = self.query_one("#buffer", Static)
        status_widget = self.query_one("#status", Static)
        mode_text = ",".join(snapshot.modes) if snapshot.modes else "-"
        buffer_widget.update(Text(snapshot.text))
        status_widget.update(
            Text(f"[{snapshot.current_buffer}] modes={mode_text} | {snapshot.status}")
        )
