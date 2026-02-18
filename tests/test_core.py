from pathlib import Path

import pytest

from pymacs.commands import register_builtin_commands
from pymacs.core import Editor


def test_builtin_commands_smoke() -> None:
    editor = Editor()
    register_builtin_commands(editor)

    editor.run("switch-to-buffer", "notes")
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


def test_window_split_and_navigation() -> None:
    editor = Editor()
    register_builtin_commands(editor)

    assert editor.window_list() == [1]

    editor.run("switch-to-buffer", "notes")
    editor.run("split-window-right")
    windows = editor.window_list()
    assert len(windows) == 2
    assert editor.selected_window_id == windows[0]

    editor.run("other-window")
    assert editor.selected_window_id == windows[1]

    editor.run("switch-to-buffer", "docs")
    assert editor.window_buffer(windows[1]) == "docs"

    editor.run("delete-other-windows")
    assert editor.window_list() == [windows[1]]


def test_window_local_point_memory() -> None:
    editor = Editor()
    register_builtin_commands(editor)

    editor.run("switch-to-buffer", "notes")
    editor.run("insert", "abcdef")
    window_a = editor.selected_window_id

    editor.run("split-window-below")
    window_b = [wid for wid in editor.window_list() if wid != window_a][0]

    editor.run("other-window")
    assert editor.selected_window_id == window_b
    editor.run("move-beginning-of-line")
    assert editor.state.window_cursor(window_b) == 0

    editor.run("other-window")
    assert editor.selected_window_id == window_a
    assert editor.state.window_cursor(window_a) == 6


def test_kill_buffer_falls_back_to_recent_buffer() -> None:
    editor = Editor()
    register_builtin_commands(editor)

    editor.run("switch-to-buffer", "a")
    editor.run("split-window-right")
    first_window, second_window = editor.window_list()

    editor.run("other-window")
    assert editor.selected_window_id == second_window
    editor.run("switch-to-buffer", "b")

    editor.run("other-window")
    assert editor.selected_window_id == first_window
    assert editor.window_buffer(first_window) == "a"

    status = editor.run("kill-buffer", "a")
    assert isinstance(status, str)
    assert "killed a" in status
    assert editor.window_buffer(first_window) == "b"


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
