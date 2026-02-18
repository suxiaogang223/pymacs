"""Programmable editor core."""

from __future__ import annotations

import inspect
import logging
from collections import defaultdict
from collections.abc import Callable
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

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
        if not path.is_file():
            raise FileNotFoundError(f"plugin path does not exist: {path}")
        spec = spec_from_file_location(path.stem, path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"cannot load plugin from {path}")
        module = module_from_spec(spec)
        spec.loader.exec_module(module)
        activate = getattr(module, "activate", None)
        if not callable(activate):
            raise TypeError(f"plugin {path} must define activate(editor)")
        params = list(inspect.signature(activate).parameters.values())
        if len(params) != 1:
            raise TypeError(f"plugin {path} activate(editor) must accept exactly one argument")
        activate(self)
        self._plugins[str(path)] = module

    def eval(self, code: str) -> object:
        """Evaluate runtime Python with controlled globals and editor local."""

        globals_scope = {"__builtins__": __builtins__}
        locals_scope = {"editor": self}
        try:
            compiled = compile(code, "<pymacs-eval>", "eval")
        except SyntaxError:
            exec(compile(code, "<pymacs-eval>", "exec"), globals_scope, locals_scope)
            return None
        return eval(compiled, globals_scope, locals_scope)

    @property
    def commands(self) -> list[str]:
        return sorted(self._commands)

    @property
    def plugins(self) -> list[str]:
        return sorted(self._plugins)
