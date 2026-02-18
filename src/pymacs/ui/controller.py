"""UI adapter that maps user input to editor operations."""

from __future__ import annotations

import shlex
from dataclasses import dataclass

from ..core import Editor
from ..keymap import KeySequence, format_key_sequence, parse_key_sequence

DEFAULT_EDIT_BINDINGS: tuple[tuple[str, str], ...] = (
    ("C-m", "newline"),
    ("C-h", "delete-backward-char"),
    ("C-d", "delete-forward-char"),
    ("C-f", "forward-char"),
    ("C-b", "backward-char"),
    ("C-a", "move-beginning-of-line"),
    ("C-e", "move-end-of-line"),
    ("C-n", "next-line"),
    ("C-p", "previous-line"),
    ("C-k", "kill-line"),
)

UI_ACTION_BINDINGS: dict[KeySequence, str] = {
    ("M-x",): "open-minibuffer",
    ("C-g",): "cancel-minibuffer",
    ("C-q",): "quit",
    ("C-x", "C-c"): "quit",
}


@dataclass(frozen=True)
class UISnapshot:
    """Immutable UI state for rendering."""

    current_buffer: str
    text: str
    cursor: int
    line: int
    col: int
    modes: tuple[str, ...]
    status: str


class UIController:
    """Stateful adapter between UI events and editor core APIs."""

    def __init__(self, editor: Editor) -> None:
        self.editor = editor
        self._status = "ready"
        self._pending_keys: list[str] = []
        self._ui_action: str | None = None
        self._bind_default_edit_keys()

    def snapshot(self) -> UISnapshot:
        text = self.editor.state.current_text()
        cursor = self.editor.state.current_cursor()
        line_start = text.rfind("\n", 0, cursor) + 1
        line = text.count("\n", 0, cursor) + 1
        col = cursor - line_start + 1
        return UISnapshot(
            current_buffer=self.editor.state.current_buffer,
            text=text,
            cursor=cursor,
            line=line,
            col=col,
            modes=tuple(self.editor.state.current_modes()),
            status=self._status,
        )

    def handle_text_input(self, text: str) -> str:
        if not text:
            return self._status
        self._pending_keys.clear()
        self._ui_action = None
        self.editor.run("insert", text)
        if text == "\n":
            return self._set_status("inserted newline")
        return self._set_status(f"inserted {len(text)} char(s)")

    def handle_backspace(self) -> str:
        self._pending_keys.clear()
        self._ui_action = None
        before = self.editor.state.current_cursor()
        self.editor.run("delete-backward-char")
        after = self.editor.state.current_cursor()
        if before == after:
            return self._set_status("buffer start")
        return self._set_status("backspace")

    def dispatch_key_chord(self, chord: str) -> str:
        try:
            sequence = parse_key_sequence(chord)
        except ValueError as exc:
            self._pending_keys.clear()
            self._ui_action = None
            return self._set_status(str(exc))

        status = self._status
        for key in sequence:
            status = self._dispatch_single_key(key)
        return status

    def has_pending_keys(self) -> bool:
        return bool(self._pending_keys)

    def pop_ui_action(self) -> str | None:
        action = self._ui_action
        self._ui_action = None
        return action

    def execute_key(self, sequence: str, *args: object) -> str:
        self._pending_keys.clear()
        self._ui_action = None
        try:
            result = self.editor.command_execute(sequence, *args)
        except KeyError as exc:
            return self._set_status(exc.args[0])
        except Exception as exc:
            return self._set_status(f"command error: {exc}")
        if result is None:
            return self._set_status(f"executed {sequence}")
        return self._set_status(str(result))

    def execute_minibuffer(self, line: str) -> str:
        try:
            parts = shlex.split(line)
        except ValueError as exc:
            return self._set_status(f"parse error: {exc}")

        if not parts:
            return self._set_status("empty command")

        cmd, args = parts[0], parts[1:]
        try:
            if cmd == "run":
                return self._run_command(args)
            if cmd == "bind":
                return self._bind_command(args)
            if cmd == "press":
                return self._press_command(args)
            if cmd == "mode":
                return self._mode_command(args)
            if cmd == "modes":
                modes = self.editor.state.current_modes()
                return self._set_status(", ".join(modes) if modes else "(none)")
            if cmd == "buf":
                return self._set_status(self.editor.state.current_buffer)
            if cmd == "commands":
                return self._set_status(" ".join(self.editor.commands))
            if cmd == "help":
                return self._set_status("commands: run bind press mode modes buf commands help")
            return self._set_status(f"unknown command: {cmd}")
        except KeyError as exc:
            return self._set_status(exc.args[0])
        except ValueError as exc:
            return self._set_status(str(exc))
        except Exception as exc:
            return self._set_status(f"command error: {exc}")

    def _dispatch_single_key(self, key: str) -> str:
        if key == "C-g":
            self._pending_keys.clear()
            self._ui_action = "cancel-minibuffer"
            return self._set_status("cancelled")

        candidate = tuple([*self._pending_keys, key])
        self._ui_action = None

        action = UI_ACTION_BINDINGS.get(candidate)
        if action is not None:
            self._pending_keys.clear()
            self._ui_action = action
            return self._set_status(self._action_status(action))

        try:
            command_name = self.editor.resolve_key(candidate)
        except KeyError:
            command_name = None

        if command_name is not None:
            self._pending_keys.clear()
            return self.execute_key(format_key_sequence(candidate))

        has_prefix = self.editor.has_prefix_binding(candidate) or self._has_ui_prefix(candidate)
        if has_prefix:
            self._pending_keys = list(candidate)
            return self._set_status(f"pending {format_key_sequence(candidate)}")

        self._pending_keys.clear()
        return self._set_status(f"unbound key sequence: {format_key_sequence(candidate)}")

    def _run_command(self, args: list[str]) -> str:
        if not args:
            return self._set_status("usage: run <cmd> [args...]")
        name, rest = args[0], args[1:]
        result = self.editor.run(name, *rest)
        if result is None:
            return self._set_status(f"ran {name}")
        return self._set_status(str(result))

    def _bind_command(self, args: list[str]) -> str:
        if len(args) < 2:
            return self._set_status("usage: bind <key> <cmd> [global|buffer|mode:<name>]")

        key, command_name = args[0], args[1]
        scope_spec = args[2] if len(args) >= 3 else "global"

        if scope_spec == "global":
            self.editor.bind_key(key, command_name, scope="global")
            return self._set_status(f"bound {key} -> {command_name} (global)")

        if scope_spec == "buffer":
            self.editor.bind_key(key, command_name, scope="buffer")
            return self._set_status(
                f"bound {key} -> {command_name} (buffer:{self.editor.state.current_buffer})"
            )

        if scope_spec.startswith("mode:"):
            mode = scope_spec.split(":", 1)[1]
            if not mode:
                return self._set_status("usage: bind <key> <cmd> [global|buffer|mode:<name>]")
            self.editor.bind_key(key, command_name, scope="mode", mode=mode)
            return self._set_status(f"bound {key} -> {command_name} (mode:{mode})")

        return self._set_status("usage: bind <key> <cmd> [global|buffer|mode:<name>]")

    def _press_command(self, args: list[str]) -> str:
        if not args:
            return self._set_status("usage: press <key> [args...]")
        key, rest = args[0], args[1:]
        if rest:
            return self.execute_key(key, *rest)
        return self.dispatch_key_chord(key)

    def _mode_command(self, args: list[str]) -> str:
        if not args:
            return self._set_status("usage: mode <name> [on|off]")
        mode = args[0]
        action = args[1] if len(args) >= 2 else "on"
        if action == "on":
            self.editor.enable_mode(mode)
            return self._set_status(f"mode {mode}: on")
        if action == "off":
            self.editor.disable_mode(mode)
            return self._set_status(f"mode {mode}: off")
        return self._set_status("usage: mode <name> [on|off]")

    def _set_status(self, message: str) -> str:
        self._status = message
        return message

    def _bind_default_edit_keys(self) -> None:
        for sequence, command_name in DEFAULT_EDIT_BINDINGS:
            try:
                key = parse_key_sequence(sequence)
            except ValueError:
                continue
            if key in self.editor.state.global_keymap:
                continue
            try:
                self.editor.bind_key(key, command_name, scope="global")
            except KeyError:
                continue

    def _has_ui_prefix(self, sequence: KeySequence) -> bool:
        for bound in UI_ACTION_BINDINGS:
            if len(bound) <= len(sequence):
                continue
            if bound[: len(sequence)] == sequence:
                return True
        return False

    def _action_status(self, action: str) -> str:
        if action == "open-minibuffer":
            return "open minibuffer"
        if action == "cancel-minibuffer":
            return "cancelled"
        if action == "quit":
            return "quit requested"
        return action
