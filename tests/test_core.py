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
    assert editor.get_command_info("insert").source_kind == "builtin"


def test_runtime_command_metadata() -> None:
    editor = Editor()

    def echo_value(_ed: Editor, value: str) -> str:
        """Return VALUE as a string."""
        return value

    editor.command("echo-value", echo_value)

    info = editor.get_command_info("echo-value")
    assert info.name == "echo-value"
    assert info.doc == "Return VALUE as a string."
    assert "value: str" in info.signature
    assert info.source_kind == "runtime"
    assert any(command.name == "echo-value" for command in editor.command_infos())


def test_emacs_style_cursor_editing_commands() -> None:
    editor = Editor()
    register_builtin_commands(editor)

    editor.run("insert", "abc")
    editor.run("backward-char")
    editor.run("insert", "X")
    assert editor.run("show-buffer") == "abXc"

    editor.run("delete-backward-char")
    assert editor.run("show-buffer") == "abc"

    editor.run("move-beginning-of-line")
    editor.run("delete-forward-char")
    assert editor.run("show-buffer") == "bc"


def test_line_navigation_and_kill_line() -> None:
    editor = Editor()
    register_builtin_commands(editor)

    editor.run("insert", "abc")
    editor.run("newline")
    editor.run("insert", "def")

    editor.run("previous-line")
    editor.run("move-end-of-line")
    editor.run("kill-line")
    assert editor.run("show-buffer") == "abcdef"

    editor.run("move-beginning-of-line")
    editor.run("forward-char", "2")
    editor.run("kill-line")
    assert editor.run("show-buffer") == "ab"


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
        "        '''Return pong from plugin.'''\n"
        "        return 'pong'\n"
        "    editor.command('ping', ping)\n",
        encoding="utf-8",
    )

    editor = Editor()
    editor.load_plugin(str(plugin))
    assert editor.run("ping") == "pong"
    info = editor.get_command_info("ping")
    assert info.source_kind == "plugin"
    assert "plugin" in info.doc


def test_load_plugin_requires_activate(tmp_path: Path) -> None:
    plugin = tmp_path / "bad_plugin.py"
    plugin.write_text("x = 1\n", encoding="utf-8")

    editor = Editor()
    with pytest.raises(TypeError, match="must define activate"):
        editor.load_plugin(str(plugin))
