import asyncio

import pytest
from rich.text import Text
from textual.widgets import Input, Static

from pymacs.ui.app import PyMACSTuiApp


def _plain_text(widget: Static) -> str:
    renderable = widget.renderable
    if isinstance(renderable, Text):
        return renderable.plain
    return str(renderable)


def test_tui_renders_initial_buffer() -> None:
    async def scenario() -> None:
        app = PyMACSTuiApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            status = _plain_text(app.query_one("#status", Static))
            assert "*scratch*" in status
            assert "line=1 col=1" in status

    asyncio.run(scenario())


def test_tui_typing_and_minibuffer_command() -> None:
    async def scenario() -> None:
        app = PyMACSTuiApp()
        async with app.run_test() as pilot:
            await pilot.press("h", "i")
            await pilot.pause()
            assert _plain_text(app.query_one("#buffer", Static)) == "hi|"

            await pilot.press("alt+x")
            await pilot.pause()
            minibuffer = app.query_one("#minibuffer", Input)
            assert minibuffer.display
            minibuffer.value = "run show-buffer"
            await pilot.press("enter")
            await pilot.pause()

            status = _plain_text(app.query_one("#status", Static))
            assert "hi" in status

    asyncio.run(scenario())


def test_tui_has_emacs_default_bindings() -> None:
    app = PyMACSTuiApp()
    assert app.editor.resolve_key("C-f") == "forward-char"
    assert app.editor.resolve_key("C-b") == "backward-char"
    assert app.editor.resolve_key("C-a") == "move-beginning-of-line"
    assert app.editor.resolve_key("C-e") == "move-end-of-line"
    assert app.editor.resolve_key("C-k") == "kill-line"
    assert app.editor.resolve_key("DEL") == "delete-backward-char"

    with pytest.raises(KeyError, match="unbound key sequence"):
        app.editor.resolve_key("C-h")
    with pytest.raises(KeyError, match="unbound key sequence"):
        app.editor.resolve_key("C-q")


def test_tui_ctrl_q_requests_quit() -> None:
    async def scenario() -> None:
        app = PyMACSTuiApp()
        async with app.run_test() as pilot:
            await pilot.press("ctrl+q")
            await pilot.pause()
            assert app.quit_requested

    asyncio.run(scenario())


def test_tui_ctrl_x_ctrl_c_requests_quit() -> None:
    async def scenario() -> None:
        app = PyMACSTuiApp()
        async with app.run_test() as pilot:
            app.controller.dispatch_key_chord("C-x")
            app.controller.dispatch_key_chord("C-c")
            app._apply_ui_action()
            await pilot.pause()
            assert app.quit_requested

    asyncio.run(scenario())


def test_tui_help_describe_command_via_c_h_f() -> None:
    async def scenario() -> None:
        app = PyMACSTuiApp()
        async with app.run_test() as pilot:
            await pilot.press("ctrl+h", "f")
            await pilot.pause()
            minibuffer = app.query_one("#minibuffer", Input)
            assert minibuffer.display
            assert minibuffer.placeholder == "Describe command:"

            minibuffer.value = "show-buffer"
            await pilot.press("enter")
            await pilot.pause()

            status = _plain_text(app.query_one("#status", Static))
            assert "*Help*" in status
            assert "help: show-buffer" in status
            assert "show-buffer" in _plain_text(app.query_one("#buffer", Static))

    asyncio.run(scenario())


def test_tui_help_describe_key_via_c_h_k() -> None:
    async def scenario() -> None:
        app = PyMACSTuiApp()
        async with app.run_test() as pilot:
            await pilot.press("ctrl+h", "k")
            await pilot.pause()
            minibuffer = app.query_one("#minibuffer", Input)
            assert minibuffer.display
            assert minibuffer.placeholder == "Describe key:"

            minibuffer.value = "C-f"
            await pilot.press("enter")
            await pilot.pause()

            help_text = _plain_text(app.query_one("#buffer", Static))
            assert "C-f" in help_text
            assert "forward-char" in help_text

    asyncio.run(scenario())


def test_tui_help_where_is_via_c_h_w() -> None:
    async def scenario() -> None:
        app = PyMACSTuiApp()
        async with app.run_test() as pilot:
            await pilot.press("ctrl+h", "w")
            await pilot.pause()
            minibuffer = app.query_one("#minibuffer", Input)
            assert minibuffer.display
            assert minibuffer.placeholder == "Where is command:"

            minibuffer.value = "forward-char"
            await pilot.press("enter")
            await pilot.pause()

            help_text = _plain_text(app.query_one("#buffer", Static))
            assert "forward-char" in help_text
            assert "C-f" in help_text

    asyncio.run(scenario())


def test_tui_backspace_routes_to_del_binding() -> None:
    async def scenario() -> None:
        app = PyMACSTuiApp()
        async with app.run_test() as pilot:
            await pilot.press("h", "i")
            await pilot.press("backspace")
            await pilot.pause()
            assert _plain_text(app.query_one("#buffer", Static)) == "h|"

    asyncio.run(scenario())
