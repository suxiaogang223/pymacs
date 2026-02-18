import pytest

from pymacs.core import Editor
from pymacs.keymap import parse_key_sequence


def test_parse_key_sequence_normalizes_tokens() -> None:
    assert parse_key_sequence("C-X M-S-f") == ("C-x", "M-S-f")
    assert parse_key_sequence(["ctrl-a", "ALT-b"]) == ("C-a", "M-b")


def test_parse_key_sequence_rejects_invalid_modifier() -> None:
    with pytest.raises(ValueError, match="unknown key modifier"):
        parse_key_sequence("Q-a")


def test_command_execute_via_global_keymap() -> None:
    editor = Editor()
    editor.command("echo", lambda _ed, value: value)
    editor.bind_key("C-e", "echo")

    assert editor.command_execute("ctrl-e", "ok") == "ok"


def test_keymap_layering_mode_over_buffer_over_global() -> None:
    editor = Editor()
    editor.command("global-cmd", lambda _ed: "global")
    editor.command("buffer-cmd", lambda _ed: "buffer")
    editor.command("mode-cmd", lambda _ed: "mode")

    editor.bind_key("C-x", "global-cmd", scope="global")
    editor.bind_key("C-x", "buffer-cmd", scope="buffer")
    assert editor.command_execute("C-x") == "buffer"

    editor.bind_key("C-x", "mode-cmd", scope="mode", mode="insert")
    editor.enable_mode("insert")
    assert editor.command_execute("C-x") == "mode"

    editor.disable_mode("insert")
    assert editor.command_execute("C-x") == "buffer"


def test_mode_precedence_is_last_enabled_first() -> None:
    editor = Editor()
    editor.command("mode-a", lambda _ed: "A")
    editor.command("mode-b", lambda _ed: "B")

    editor.bind_key("C-k", "mode-a", scope="mode", mode="a")
    editor.bind_key("C-k", "mode-b", scope="mode", mode="b")
    editor.enable_mode("a")
    editor.enable_mode("b")

    assert editor.command_execute("C-k") == "B"


def test_unbound_key_sequence_raises() -> None:
    editor = Editor()
    with pytest.raises(KeyError, match="unbound key sequence"):
        editor.command_execute("C-z")
