"""Programmable editor core."""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Callable
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from .keymap import KeySequenceInput, format_key_sequence, parse_key_sequence
from .state import EditorState

Command = Callable[..., object]
Hook = Callable[..., object]
logger = logging.getLogger(__name__)


class Editor:
    """Live editor runtime with command/hook/plugin APIs."""

    def __init__(self) -> None:
        self.state = EditorState()
        self._commands: dict[str, Command] = {}
        self._hooks: dict[str, list[Hook]] = defaultdict(list)
        self._plugins: dict[str, object] = {}

    def command(self, name: str, fn: Command) -> None:
        self._commands[name] = fn

    def run(self, name: str, *args: object) -> object:
        cmd = self._commands.get(name)
        if cmd is None:
            raise KeyError(f"unknown command: {name}")
        self.emit("before-command", name, args)
        result = cmd(self, *args)
        self.emit("after-command", name, args, result)
        return result

    def on(self, event: str, fn: Hook) -> None:
        self._hooks[event].append(fn)

    def emit(self, event: str, *args: object) -> None:
        for fn in self._hooks.get(event, []):
            try:
                fn(self, *args)
            except Exception:
                logger.exception("hook failed for event %s", event)

    def load_plugin(self, plugin_path: str) -> None:
        path = Path(plugin_path).expanduser().resolve()
        spec = spec_from_file_location(path.stem, path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"cannot load plugin from {path}")
        module = module_from_spec(spec)
        spec.loader.exec_module(module)
        activate = getattr(module, "activate", None)
        if not callable(activate):
            raise TypeError(f"plugin {path} must define activate(editor)")
        activate(self)
        self._plugins[str(path)] = module

    def bind_key(
        self,
        sequence: KeySequenceInput,
        command_name: str,
        *,
        scope: str = "global",
        buffer: str | None = None,
        mode: str | None = None,
    ) -> None:
        if command_name not in self._commands:
            raise KeyError(f"unknown command: {command_name}")

        key = parse_key_sequence(sequence)

        if scope == "global":
            self.state.global_keymap[key] = command_name
            return

        if scope == "buffer":
            target = buffer or self.state.current_buffer
            self.state.buffer_keymaps.setdefault(target, {})[key] = command_name
            return

        if scope == "mode":
            if not mode:
                raise ValueError("mode name required for mode scope")
            self.state.mode_keymaps.setdefault(mode, {})[key] = command_name
            return

        raise ValueError(f"unknown keymap scope: {scope}")

    def enable_mode(self, mode: str, *, buffer: str | None = None) -> None:
        target = buffer or self.state.current_buffer
        modes = self.state.buffer_modes.setdefault(target, [])
        if mode not in modes:
            modes.append(mode)

    def disable_mode(self, mode: str, *, buffer: str | None = None) -> None:
        target = buffer or self.state.current_buffer
        modes = self.state.buffer_modes.get(target)
        if not modes:
            return
        if mode in modes:
            modes.remove(mode)

    def resolve_key(self, sequence: KeySequenceInput, *, buffer: str | None = None) -> str:
        key = parse_key_sequence(sequence)
        target = buffer or self.state.current_buffer

        for mode in reversed(self.state.buffer_modes.get(target, [])):
            command_name = self.state.mode_keymaps.get(mode, {}).get(key)
            if command_name is not None:
                return command_name

        command_name = self.state.buffer_keymaps.get(target, {}).get(key)
        if command_name is not None:
            return command_name

        command_name = self.state.global_keymap.get(key)
        if command_name is not None:
            return command_name

        raise KeyError(f"unbound key sequence: {format_key_sequence(key)}")

    def command_execute(
        self,
        sequence: KeySequenceInput,
        *args: object,
        buffer: str | None = None,
    ) -> object:
        command_name = self.resolve_key(sequence, buffer=buffer)
        return self.run(command_name, *args)

    @property
    def commands(self) -> list[str]:
        return sorted(self._commands)
