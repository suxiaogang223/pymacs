from pathlib import Path

import pytest

from pymacs.commands import register_builtin_commands
from pymacs.core import Editor


def test_builtin_commands_smoke() -> None:
    editor = Editor()
    register_builtin_commands(editor)

    editor.run("new-buffer", "notes")
    editor.run("switch-buffer", "notes")
    editor.run("insert", "hello", "world")
    assert editor.run("show-buffer") == "hello world"

    editor.run("set", "theme", "dark")
    assert editor.run("get", "theme") == "dark"


def test_hook_failure_isolated(caplog: pytest.LogCaptureFixture) -> None:
    editor = Editor()

    def explode(_ed: Editor, *_args: object) -> None:
        raise RuntimeError("hook boom")

    def echo(_ed: Editor, value: str) -> str:
        return value

    editor.command("echo", echo)
    editor.on("before-command", explode)

    with caplog.at_level("ERROR"):
        assert editor.run("echo", "ok") == "ok"
    assert "hook failed for event before-command" in caplog.text


def test_load_plugin_registers_command(tmp_path: Path) -> None:
    plugin = tmp_path / "demo_plugin.py"
    plugin.write_text(
        "def activate(editor):\n"
        "    def ping(ed):\n"
        "        return 'pong'\n"
        "    editor.command('ping', ping)\n",
        encoding="utf-8",
    )

    editor = Editor()
    editor.load_plugin(str(plugin))
    assert editor.run("ping") == "pong"


def test_load_plugin_requires_activate(tmp_path: Path) -> None:
    plugin = tmp_path / "bad_plugin.py"
    plugin.write_text("x = 1\n", encoding="utf-8")

    editor = Editor()
    with pytest.raises(TypeError, match="must define activate"):
        editor.load_plugin(str(plugin))
