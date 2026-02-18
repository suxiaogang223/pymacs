"""TUI entrypoint."""

from __future__ import annotations

from .ui.app import PyMACSTuiApp


def run_tui() -> None:
    app = PyMACSTuiApp()
    app.run()
