"""Programmable editor core."""

from __future__ import annotations

import inspect
import logging
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from .keymap import KeySequence, KeySequenceInput, format_key_sequence, parse_key_sequence
from .state import EditorState

Command = Callable[..., object]
Hook = Callable[..., object]
logger = logging.getLogger(__name__)

_SOURCE_KINDS = {"builtin", "plugin", "runtime"}


@dataclass(frozen=True)
class CommandInfo:
    """Command registration metadata."""

    name: str
    fn: Command
    doc: str
    signature: str
    module: str
    source_kind: str


@dataclass(frozen=True)
class KeyBindingInfo:
    """Resolved key binding metadata."""

    sequence: KeySequence
    command_name: str
    scope: str
    buffer: str | None = None
    mode: str | None = None


class Editor:
    """Live editor runtime with command/hook/plugin APIs."""

    def __init__(self) -> None:
        self.state = EditorState()
        self._commands: dict[str, CommandInfo] = {}
        self._hooks: dict[str, list[Hook]] = defaultdict(list)
        self._plugins: dict[str, object] = {}
        self._registration_source_kind = "runtime"

    def command(self, name: str, fn: Command, *, source_kind: str | None = None) -> None:
        kind = self._normalize_source_kind(source_kind or self._registration_source_kind)
        doc = inspect.getdoc(fn) or "(undocumented command)"
        module_name = str(getattr(fn, "__module__", ""))
        try:
            signature = str(inspect.signature(fn))
        except (TypeError, ValueError):
            signature = "(...)"

        self._commands[name] = CommandInfo(
            name=name,
            fn=fn,
            doc=doc,
            signature=signature,
            module=module_name,
            source_kind=kind,
        )

    def get_command_info(self, name: str) -> CommandInfo:
        command = self._commands.get(name)
        if command is None:
            raise KeyError(f"unknown command: {name}")
        return command

    def command_infos(self) -> list[CommandInfo]:
        return [self._commands[name] for name in self.commands]

    def run(self, name: str, *args: object) -> object:
        info = self._commands.get(name)
        if info is None:
            raise KeyError(f"unknown command: {name}")
        self.emit("before-command", name, args)
        result = info.fn(self, *args)
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

        previous_source_kind = self._registration_source_kind
        self._registration_source_kind = "plugin"
        try:
            activate(self)
        finally:
            self._registration_source_kind = previous_source_kind
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
            target = buffer or self.state.selected_buffer()
            self.state.buffer_keymaps.setdefault(target, {})[key] = command_name
            return

        if scope == "mode":
            if not mode:
                raise ValueError("mode name required for mode scope")
            self.state.mode_keymaps.setdefault(mode, {})[key] = command_name
            return

        raise ValueError(f"unknown keymap scope: {scope}")

    def enable_mode(self, mode: str, *, buffer: str | None = None) -> None:
        target = buffer or self.state.selected_buffer()
        modes = self.state.buffer_modes.setdefault(target, [])
        if mode not in modes:
            modes.append(mode)

    def disable_mode(self, mode: str, *, buffer: str | None = None) -> None:
        target = buffer or self.state.selected_buffer()
        modes = self.state.buffer_modes.get(target)
        if not modes:
            return
        if mode in modes:
            modes.remove(mode)

    def resolve_key(self, sequence: KeySequenceInput, *, buffer: str | None = None) -> str:
        return self.describe_key(sequence, buffer=buffer).command_name

    def describe_key(self, sequence: KeySequenceInput, *, buffer: str | None = None) -> KeyBindingInfo:
        key = parse_key_sequence(sequence)
        target = buffer or self.state.selected_buffer()

        for scope, mode_name, target_buffer, keymap in self._active_keymaps(target):
            command_name = keymap.get(key)
            if command_name is None:
                continue
            return KeyBindingInfo(
                sequence=key,
                command_name=command_name,
                scope=scope,
                buffer=target_buffer,
                mode=mode_name,
            )

        raise KeyError(f"unbound key sequence: {format_key_sequence(key)}")

    def where_is(self, name: str, *, buffer: str | None = None) -> list[KeyBindingInfo]:
        if name not in self._commands:
            raise KeyError(f"unknown command: {name}")

        target = buffer or self.state.selected_buffer()
        bindings: list[KeyBindingInfo] = []

        for scope, mode_name, target_buffer, keymap in self._active_keymaps(target):
            for sequence, command_name in sorted(keymap.items(), key=lambda item: item[0]):
                if command_name != name:
                    continue
                bindings.append(
                    KeyBindingInfo(
                        sequence=sequence,
                        command_name=command_name,
                        scope=scope,
                        buffer=target_buffer,
                        mode=mode_name,
                    )
                )

        return bindings

    def has_prefix_binding(self, sequence: KeySequenceInput, *, buffer: str | None = None) -> bool:
        key = parse_key_sequence(sequence)
        target = buffer or self.state.selected_buffer()

        for _scope, _mode_name, _target_buffer, keymap in self._active_keymaps(target):
            for bound_sequence in keymap:
                if len(bound_sequence) <= len(key):
                    continue
                if bound_sequence[: len(key)] == key:
                    return True
        return False

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

    @property
    def selected_window_id(self) -> int:
        return self.state.selected_window_id

    def window_list(self) -> list[int]:
        return self.state.window_list()

    def window_buffer(self, window_id: int) -> str:
        return self.state.window_buffer(window_id)

    def set_window_buffer(self, window_id: int, buffer_name: str) -> None:
        self.state.set_window_buffer(window_id, buffer_name)

    def split_window_below(self) -> int:
        return self.state.split_selected_window("below")

    def split_window_right(self) -> int:
        return self.state.split_selected_window("right")

    def other_window(self) -> int:
        return self.state.other_window()

    def delete_window(self) -> int:
        return self.state.delete_window()

    def delete_other_windows(self) -> int:
        return self.state.delete_other_windows()

    def pop_to_buffer(self, buffer_name: str, *, prefer_other: bool = True) -> int:
        return self.state.pop_to_buffer(buffer_name, prefer_other=prefer_other)

    def _active_keymaps(
        self,
        buffer: str,
    ) -> list[tuple[str, str | None, str | None, dict[KeySequence, str]]]:
        active: list[tuple[str, str | None, str | None, dict[KeySequence, str]]] = []

        for mode_name in reversed(self.state.buffer_modes.get(buffer, [])):
            active.append(("mode", mode_name, buffer, self.state.mode_keymaps.get(mode_name, {})))

        active.append(("buffer", None, buffer, self.state.buffer_keymaps.get(buffer, {})))
        active.append(("global", None, None, self.state.global_keymap))
        return active

    def _normalize_source_kind(self, source_kind: str) -> str:
        if source_kind in _SOURCE_KINDS:
            return source_kind
        return "runtime"
