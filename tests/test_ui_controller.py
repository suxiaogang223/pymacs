from pymacs.commands import register_builtin_commands
from pymacs.core import Editor
from pymacs.ui.controller import UIController


def _new_controller() -> UIController:
    editor = Editor()
    register_builtin_commands(editor)
    return UIController(editor)


def test_snapshot_and_text_mutations() -> None:
    controller = _new_controller()

    snap = controller.snapshot()
    assert snap.current_buffer == "*scratch*"
    assert snap.text == ""
    assert snap.cursor == 0
    assert snap.line == 1
    assert snap.col == 1

    controller.handle_text_input("ab")
    snap = controller.snapshot()
    assert snap.text == "ab"
    assert snap.cursor == 2
    assert snap.line == 1
    assert snap.col == 3

    controller.handle_backspace()
    assert controller.snapshot().text == "a"

    controller.handle_backspace()
    assert controller.snapshot().text == ""
    assert controller.handle_backspace() == "buffer start"


def test_dispatch_key_chord_prefix_and_ui_actions() -> None:
    controller = _new_controller()

    assert controller.dispatch_key_chord("C-x") == "pending C-x"
    assert controller.has_pending_keys()
    assert controller.pop_ui_action() is None

    assert controller.dispatch_key_chord("C-c") == "quit requested"
    assert not controller.has_pending_keys()
    action = controller.pop_ui_action()
    assert action is not None
    assert action.name == "quit"

    controller.dispatch_key_chord("M-x")
    action = controller.pop_ui_action()
    assert action is not None
    assert action.name == "open-minibuffer"

    assert controller.dispatch_key_chord("C-g") == "cancelled"
    action = controller.pop_ui_action()
    assert action is not None
    assert action.name == "cancel-minibuffer"


def test_help_prefix_flow_for_describe_command() -> None:
    controller = _new_controller()

    assert controller.dispatch_key_chord("C-h") == "pending C-h"
    assert controller.has_pending_keys()
    assert controller.dispatch_key_chord("f") == "Describe command:"

    action = controller.pop_ui_action()
    assert action is not None
    assert action.name == "open-minibuffer"
    assert action.prompt == "Describe command:"

    assert controller.handle_minibuffer_submit("show-buffer") == "help: show-buffer"
    assert controller.snapshot().current_buffer == "*Help*"
    assert "show-buffer" in controller.snapshot().text


def test_help_prefix_rejects_unknown_subcommand() -> None:
    controller = _new_controller()

    assert controller.dispatch_key_chord("C-h") == "pending C-h"
    assert controller.dispatch_key_chord("z") == "unbound key sequence: C-h z"
    assert not controller.has_pending_keys()


def test_del_is_backspace_and_c_h_is_help_prefix() -> None:
    controller = _new_controller()

    controller.handle_text_input("ab")
    assert controller.dispatch_key_chord("DEL") == "executed del"
    assert controller.snapshot().text == "a"

    assert controller.dispatch_key_chord("C-h") == "pending C-h"
    assert controller.snapshot().text == "a"


def test_execute_minibuffer_happy_paths() -> None:
    controller = _new_controller()

    assert controller.execute_minibuffer("run new-buffer notes") == "ran new-buffer"
    assert controller.execute_minibuffer("run switch-buffer notes") == "ran switch-buffer"
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
