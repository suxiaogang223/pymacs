from pymacs.commands import register_builtin_commands
from pymacs.core import Editor
from pymacs.ui.controller import UIController


def _new_controller() -> UIController:
    editor = Editor()
    register_builtin_commands(editor)
    return UIController(editor)


def _selected_window(controller: UIController):
    snapshot = controller.snapshot()
    for window in snapshot.windows:
        if window.selected:
            return window
    raise AssertionError("missing selected window")


def test_snapshot_and_text_mutations() -> None:
    controller = _new_controller()

    snap = controller.snapshot()
    assert snap.selected_window_id == 1
    assert len(snap.windows) == 1
    assert _selected_window(controller).buffer == "*scratch*"
    assert _selected_window(controller).text == ""

    controller.handle_text_input("ab")
    selected = _selected_window(controller)
    assert selected.text == "ab"
    assert selected.cursor == 2

    controller.dispatch_key_chord("DEL")
    assert _selected_window(controller).text == "a"


def test_dispatch_ctrl_x_window_commands() -> None:
    controller = _new_controller()

    assert controller.dispatch_key_chord("C-x") == "pending C-x"
    assert controller.dispatch_key_chord("2") == "ran split-window-below"
    assert len(controller.snapshot().windows) == 2

    selected_before = controller.snapshot().selected_window_id
    assert controller.dispatch_key_chord("C-x") == "pending C-x"
    assert controller.dispatch_key_chord("o") == "ran other-window"
    assert controller.snapshot().selected_window_id != selected_before

    assert controller.dispatch_key_chord("C-x") == "pending C-x"
    assert controller.dispatch_key_chord("1") == "ran delete-other-windows"
    assert len(controller.snapshot().windows) == 1


def test_dispatch_ctrl_x_prompts_switch_and_kill_buffer() -> None:
    controller = _new_controller()

    assert controller.dispatch_key_chord("C-x") == "pending C-x"
    assert controller.dispatch_key_chord("b") == "Switch to buffer:"

    action = controller.pop_ui_action()
    assert action is not None
    assert action.name == "open-minibuffer"
    assert action.prompt == "Switch to buffer:"

    assert controller.handle_minibuffer_submit("notes") == "ran switch-to-buffer"
    assert _selected_window(controller).buffer == "notes"

    assert controller.dispatch_key_chord("C-x") == "pending C-x"
    assert controller.dispatch_key_chord("k") == "Kill buffer:"

    action = controller.pop_ui_action()
    assert action is not None
    assert action.prompt == "Kill buffer:"

    status = controller.handle_minibuffer_submit("notes")
    assert status.startswith("killed notes")
    assert _selected_window(controller).buffer == "*scratch*"


def test_help_prefix_flow_for_describe_command() -> None:
    controller = _new_controller()

    assert controller.dispatch_key_chord("C-x") == "pending C-x"
    assert controller.dispatch_key_chord("2") == "ran split-window-below"

    assert controller.dispatch_key_chord("C-h") == "pending C-h"
    assert controller.has_pending_keys()
    assert controller.dispatch_key_chord("f") == "Describe command:"

    action = controller.pop_ui_action()
    assert action is not None
    assert action.name == "open-minibuffer"
    assert action.prompt == "Describe command:"

    assert controller.handle_minibuffer_submit("show-buffer") == "help: show-buffer"
    snap = controller.snapshot()
    assert len(snap.windows) == 2
    assert any(window.buffer == "*Help*" for window in snap.windows)


def test_help_prefix_rejects_unknown_subcommand() -> None:
    controller = _new_controller()

    assert controller.dispatch_key_chord("C-h") == "pending C-h"
    assert controller.dispatch_key_chord("z") == "unbound key sequence: C-h z"
    assert not controller.has_pending_keys()


def test_execute_minibuffer_happy_paths() -> None:
    controller = _new_controller()

    assert controller.execute_minibuffer("run switch-to-buffer notes") == "ran switch-to-buffer"
    assert controller.execute_minibuffer("run insert hi") == "ran insert"
    assert controller.execute_minibuffer("run show-buffer") == "hi"

    assert controller.execute_minibuffer("bind C-p show-buffer") == "bound C-p -> show-buffer (global)"
    assert controller.execute_minibuffer("press C-p") == "hi"

    assert controller.execute_minibuffer("mode insert") == "mode insert: on"
    assert controller.execute_minibuffer("modes") == "insert"
    assert controller.execute_minibuffer("mode insert off") == "mode insert: off"
    assert controller.execute_minibuffer("buf") == "notes"
    assert "show-buffer" in controller.execute_minibuffer("commands")
    assert controller.execute_minibuffer("help").startswith("commands:")


def test_execute_minibuffer_error_paths() -> None:
    controller = _new_controller()

    assert controller.execute_minibuffer("") == "empty command"
    assert controller.execute_minibuffer("run") == "usage: run <cmd> [args...]"
    assert controller.execute_minibuffer("bind") == "usage: bind <key> <cmd> [global|buffer|mode:<name>]"
    assert controller.execute_minibuffer("press") == "usage: press <key> [args...]"
    assert controller.execute_minibuffer("mode") == "usage: mode <name> [on|off]"
    assert controller.execute_minibuffer("unknown") == "unknown command: unknown"
    assert controller.execute_minibuffer('run "unterminated').startswith("parse error:")
