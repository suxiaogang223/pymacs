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
    with pytest.raises(KeyError, match="unbound key sequence"):
        app.editor.resolve_key("C-q")
    with pytest.raises(KeyError, match="unbound key sequence"):
        app.editor.resolve_key("C-x C-c")


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


def test_tui_minibuffer_open_and_cancel() -> None:
    async def scenario() -> None:
        app = PyMACSTuiApp()
        async with app.run_test() as pilot:
            minibuffer = app.query_one("#minibuffer", Input)
            assert not minibuffer.display

            await pilot.press("alt+x")
            await pilot.pause()
            assert minibuffer.display

            await pilot.press("ctrl+g")
            await pilot.pause()
            assert not minibuffer.display

    asyncio.run(scenario())


def test_tui_routes_control_keys_to_controller_dispatch() -> None:
    async def scenario() -> None:
        app = PyMACSTuiApp()
        seen: list[str] = []
        original = app.controller.dispatch_key_chord

        def wrapped(chord: str) -> str:
            seen.append(chord)
            return original(chord)

        app.controller.dispatch_key_chord = wrapped
        async with app.run_test() as pilot:
            await pilot.press("ctrl+f", "ctrl+b")
            await pilot.pause()

        assert seen[:2] == ["C-f", "C-b"]

    asyncio.run(scenario())
