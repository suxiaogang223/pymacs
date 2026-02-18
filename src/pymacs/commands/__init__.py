"""Built-in command registration entrypoint."""

from __future__ import annotations

from ..core import Editor
from .editing import register_editing_commands
from .help import register_help_commands

__all__ = ["register_builtin_commands", "register_editing_commands", "register_help_commands"]


def register_builtin_commands(editor: Editor) -> None:
    """Register all built-in commands on an editor instance."""
    register_editing_commands(editor)
    register_help_commands(editor)
