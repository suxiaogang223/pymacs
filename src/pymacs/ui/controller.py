"""UI adapter that maps user input to editor operations."""

from __future__ import annotations

import shlex
from dataclasses import dataclass

from ..core import Editor


@dataclass(frozen=True)
class UISnapshot:
    """Immutable UI state for rendering."""

    current_buffer: str
    text: str
    modes: tuple[str, ...]
    status: str


class UIController:
    """Stateful adapter between UI events and editor core APIs."""

    def __init__(self, editor: Editor) -> None:
        self.editor = editor
        self._status = "ready"

    def snapshot(self) -> UISnapshot:
        return UISnapshot(
            current_buffer=self.editor.state.current_buffer,
            text=self.editor.state.current_text(),
            modes=tuple(self.editor.state.current_modes()),
            status=self._status,
        )

    def handle_text_input(self, text: str) -> str:
        if not text:
            return self._status
        self.editor.run("insert", text)
        if text == "\n":
            return self._set_status("inserted newline")
        return self._set_status(f"inserted {len(text)} char(s)")

    def handle_backspace(self) -> str:
        current = self.editor.state.current_text()
        if not current:
            return self._set_status("buffer start")
        self.editor.state.set_current_text(current[:-1])
        return self._set_status("backspace")

    def execute_key(self, sequence: str, *args: object) -> str:
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
        return self.execute_key(key, *rest)

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
