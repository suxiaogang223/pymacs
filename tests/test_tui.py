import asyncio

import pytest
from rich.layout import Layout
from rich.panel import Panel
from textual.widgets import Input, Static

from pymacs.ui.app import PyMACSTuiApp


def _selected_window(app: PyMACSTuiApp):
    snapshot = app.controller.snapshot()
    for window in snapshot.windows:
        if window.selected:
            return window
    raise AssertionError("missing selected window")


def _collect_panels(layout: Layout) -> list[Panel]:
    if layout.children:
        panels: list[Panel] = []
        for child in layout.children:
            panels.extend(_collect_panels(child))
        return panels

    if isinstance(layout.renderable, Panel):
        return [layout.renderable]

    return []


def test_tui_renders_initial_workspace() -> None:
    async def scenario() -> None:
        app = PyMACSTuiApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            workspace = app.query_one("#workspace", Static)
            assert isinstance(workspace.renderable, Layout)
            status = app.query_one("#status", Static).renderable
            assert "windows=1" in str(status)

    asyncio.run(scenario())


def test_tui_typing_and_minibuffer_command() -> None:
    async def scenario() -> None:
        app = PyMACSTuiApp()
        async with app.run_test() as pilot:
            await pilot.press("h", "i")
            await pilot.pause()
            assert _selected_window(app).text == "hi"

            await pilot.press("alt+x")
            await pilot.pause()
            minibuffer = app.query_one("#minibuffer", Input)
            assert minibuffer.display
            minibuffer.value = "run show-buffer"
            await pilot.press("enter")
            await pilot.pause()

            status = str(app.query_one("#status", Static).renderable)
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


def test_tui_multi_window_render_and_selected_highlight() -> None:
    async def scenario() -> None:
        app = PyMACSTuiApp()
        async with app.run_test() as pilot:
            await pilot.press("ctrl+x", "2")
            await pilot.pause()

            workspace = app.query_one("#workspace", Static)
            assert isinstance(workspace.renderable, Layout)
            panels = _collect_panels(workspace.renderable)
            assert len(panels) == 2
            assert sum(1 for panel in panels if str(panel.border_style) == "bright_green") == 1

    asyncio.run(scenario())


def test_tui_ctrl_x_ctrl_b_shows_buffer_list() -> None:
    async def scenario() -> None:
        app = PyMACSTuiApp()
        async with app.run_test() as pilot:
            await pilot.press("ctrl+x", "ctrl+b")
            await pilot.pause()

            snapshot = app.controller.snapshot()
            assert any(window.buffer == "*Buffer List*" for window in snapshot.windows)

    asyncio.run(scenario())


def test_tui_help_prefers_other_window_when_available() -> None:
    async def scenario() -> None:
        app = PyMACSTuiApp()
        async with app.run_test() as pilot:
            await pilot.press("ctrl+x", "2")
            await pilot.pause()

            selected_before = _selected_window(app).window_id

            await pilot.press("ctrl+h", "f")
            await pilot.pause()
            minibuffer = app.query_one("#minibuffer", Input)
            assert minibuffer.display
            assert minibuffer.placeholder == "Describe command:"

            minibuffer.value = "show-buffer"
            await pilot.press("enter")
            await pilot.pause()

            snapshot = app.controller.snapshot()
            selected_after = _selected_window(app)
            assert selected_after.window_id == selected_before
            assert selected_after.buffer != "*Help*"
            assert any(window.buffer == "*Help*" for window in snapshot.windows)

    asyncio.run(scenario())


def test_tui_backspace_routes_to_del_binding() -> None:
    async def scenario() -> None:
        app = PyMACSTuiApp()
        async with app.run_test() as pilot:
            await pilot.press("h", "i")
            await pilot.press("backspace")
            await pilot.pause()
            assert _selected_window(app).text == "h"

    asyncio.run(scenario())
