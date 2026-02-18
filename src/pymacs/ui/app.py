"""Textual TUI application for PyMACS."""

from __future__ import annotations

from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text
from textual.app import App, ComposeResult
from textual.events import Key
from textual.widgets import Input, Static

from ..commands import register_builtin_commands
from ..core import Editor
from .controller import LayoutSnapshot, UIController, WindowSnapshot

DEFAULT_MINIBUFFER_PLACEHOLDER = "M-x command"


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


class WorkspaceView(Static):
    can_focus = True


class PyMACSTuiApp(App[None]):
    """Core Textual frontend for PyMACS."""

    CSS = """
    Screen {
        layout: vertical;
    }

    #workspace {
        height: 1fr;
        border: round $accent;
        padding: 0;
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

    @property
    def quit_requested(self) -> bool:
        return self._quit_requested

    def compose(self) -> ComposeResult:
        yield WorkspaceView(id="workspace")
        yield Static(id="status")
        yield Input(placeholder=DEFAULT_MINIBUFFER_PLACEHOLDER, id="minibuffer")

    def on_mount(self) -> None:
        self._hide_minibuffer()
        self.query_one("#workspace", WorkspaceView).focus()
        self._refresh_view()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "minibuffer":
            return
        self.controller.handle_minibuffer_submit(event.value)
        self._hide_minibuffer()
        self._apply_ui_action()
        self._refresh_view()

    def on_key(self, event: Key) -> None:
        minibuffer = self.query_one("#minibuffer", Input)
        if minibuffer.display:
            if event.key in {"escape", "ctrl+g"}:
                self.controller.dispatch_key_chord("C-g")
                self._apply_ui_action()
                self._refresh_view()
                event.stop()
            return

        if event.key == "enter":
            self.controller.dispatch_key_chord("C-m")
            self._apply_ui_action()
            self._refresh_view()
            event.stop()
            return

        if event.key == "backspace":
            self.controller.dispatch_key_chord("DEL")
            self._apply_ui_action()
            self._refresh_view()
            event.stop()
            return

        sequence = _key_to_sequence(event.key)
        if sequence is not None:
            self.controller.dispatch_key_chord(sequence)
            self._apply_ui_action()
            self._refresh_view()
            event.stop()
            return

        if event.character and event.character.isprintable():
            if self.controller.has_pending_keys():
                self.controller.dispatch_key_chord(event.character)
            else:
                self.controller.handle_text_input(event.character)
            self._apply_ui_action()
            self._refresh_view()
            event.stop()

    def _show_minibuffer(self, prompt: str | None = None) -> None:
        minibuffer = self.query_one("#minibuffer", Input)
        minibuffer.placeholder = prompt or DEFAULT_MINIBUFFER_PLACEHOLDER
        minibuffer.display = True
        minibuffer.value = ""
        minibuffer.focus()

    def _hide_minibuffer(self) -> None:
        minibuffer = self.query_one("#minibuffer", Input)
        minibuffer.placeholder = DEFAULT_MINIBUFFER_PLACEHOLDER
        minibuffer.value = ""
        minibuffer.display = False
        self.query_one("#workspace", WorkspaceView).focus()

    def _apply_ui_action(self) -> None:
        action = self.controller.pop_ui_action()
        if action is None:
            return
        if action.name == "open-minibuffer":
            self._show_minibuffer(action.prompt)
            return
        if action.name == "cancel-minibuffer":
            self._hide_minibuffer()
            return
        if action.name == "quit":
            self._quit_requested = True
            self.exit()

    def _refresh_view(self) -> None:
        snapshot = self.controller.snapshot()
        workspace_widget = self.query_one("#workspace", Static)
        status_widget = self.query_one("#status", Static)

        windows_by_id = {window.window_id: window for window in snapshot.windows}
        workspace_widget.update(self._render_layout(snapshot.layout, windows_by_id))
        status_widget.update(
            Text(
                f"windows={len(snapshot.windows)} selected={snapshot.selected_window_id} | {snapshot.status}"
            )
        )

    def _render_layout(
        self,
        layout_node: LayoutSnapshot,
        windows_by_id: dict[int, WindowSnapshot],
    ) -> Layout:
        if layout_node.kind == "window":
            window_id = layout_node.window_id
            if window_id is None:
                return Layout(name="invalid", renderable=Text("invalid window"))
            snapshot = windows_by_id.get(window_id)
            if snapshot is None:
                return Layout(name=f"window-{window_id}", renderable=Text("missing window"))
            return Layout(name=f"window-{window_id}", renderable=self._render_window(snapshot))

        root = Layout(name="split")
        if layout_node.first is None or layout_node.second is None:
            root.update(Text("invalid split"))
            return root

        first = self._render_layout(layout_node.first, windows_by_id)
        second = self._render_layout(layout_node.second, windows_by_id)

        if layout_node.axis == "below":
            root.split_column(first, second)
        else:
            root.split_row(first, second)
        return root

    def _render_window(self, window: WindowSnapshot) -> Panel:
        rendered_text = window.text[: window.cursor] + "|" + window.text[window.cursor :]
        mode_text = ",".join(window.modes) if window.modes else "-"
        local_status = Text(
            f"[{window.buffer}] line={window.line} col={window.col} modes={mode_text}",
            style="bold" if window.selected else "",
        )

        body = Layout(name=f"window-body-{window.window_id}")
        body.split_column(
            Layout(name="content", renderable=Text(rendered_text), ratio=1),
            Layout(name="mode-line", renderable=local_status, size=1),
        )
        return Panel(
            body,
            title=f"Window {window.window_id}",
            border_style="bright_green" if window.selected else "white",
            padding=(0, 1),
        )
