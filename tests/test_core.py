from pathlib import Path

import pytest

from pymacs.core import Editor
from pymacs.cli import _register_builtin_commands


def test_builtin_commands_smoke() -> None:
    editor = Editor()
    _register_builtin_commands(editor)

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


def test_load_plugin_requires_single_activate_argument(tmp_path: Path) -> None:
    plugin = tmp_path / "bad_sig_plugin.py"
    plugin.write_text(
        "def activate(editor, extra):\n"
        "    return None\n",
        encoding="utf-8",
    )

    editor = Editor()
    with pytest.raises(TypeError, match="accept exactly one argument"):
        editor.load_plugin(str(plugin))


def test_load_plugin_missing_path_raises_file_not_found() -> None:
    editor = Editor()
    with pytest.raises(FileNotFoundError, match="plugin path does not exist"):
        editor.load_plugin("/tmp/pymacs_not_exists_plugin.py")


def test_eval_supports_expression_and_exec() -> None:
    editor = Editor()
    editor.state.variables["name"] = "pymacs"

    assert editor.eval("1 + 2") == 3

    result = editor.eval("editor.state.variables['answer'] = 42")
    assert result is None
    assert editor.state.variables["answer"] == 42
