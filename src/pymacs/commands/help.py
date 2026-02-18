"""Built-in self-documenting help commands."""

from __future__ import annotations

from ..core import Editor, KeyBindingInfo
from ..keymap import format_key_sequence

HELP_BUFFER_NAME = "*Help*"


def register_help_commands(editor: Editor) -> None:
    """Register Emacs-style help commands."""

    def describe_command(ed: Editor, name: str) -> str:
        """Describe command NAME in the *Help* buffer."""
        command_name = str(name).strip()
        if not command_name:
            raise ValueError("usage: describe-command <name>")

        info = ed.get_command_info(command_name)
        lines = [
            f"{info.name} {info.signature}",
            f"Source: {info.source_kind} ({info.module})",
            "",
            info.doc,
        ]
        _show_help(ed, "\n".join(lines))
        return f"help: {info.name}"

    def describe_key(ed: Editor, *parts: object) -> str:
        """Describe command bound to key sequence."""
        sequence = _parts_to_arg(parts)
        if not sequence:
            raise ValueError("usage: describe-key <key-sequence>")

        binding = ed.describe_key(sequence)
        info = ed.get_command_info(binding.command_name)
        lines = [
            f"{format_key_sequence(binding.sequence)} runs command {binding.command_name}",
            f"Scope: {_format_scope(binding)}",
            f"Source: {info.source_kind} ({info.module})",
            "",
            info.doc,
        ]
        _show_help(ed, "\n".join(lines))
        return f"help: {format_key_sequence(binding.sequence)}"

    def where_is(ed: Editor, name: str) -> str:
        """Show active key bindings for command NAME."""
        command_name = str(name).strip()
        if not command_name:
            raise ValueError("usage: where-is <command-name>")

        bindings = ed.where_is(command_name)
        if not bindings:
            lines = [f"{command_name} is not on any key in the current context."]
        else:
            lines = [f"{command_name} is on:", ""]
            lines.extend(
                f"{format_key_sequence(binding.sequence):<12} {_format_scope(binding)}"
                for binding in bindings
            )

        _show_help(ed, "\n".join(lines))
        return f"help: {command_name}"

    editor.command("describe-command", describe_command, source_kind="builtin")
    editor.command("describe-key", describe_key, source_kind="builtin")
    editor.command("where-is", where_is, source_kind="builtin")


def _parts_to_arg(parts: tuple[object, ...]) -> str:
    return " ".join(str(part) for part in parts).strip()


def _format_scope(binding: KeyBindingInfo) -> str:
    if binding.scope == "mode" and binding.mode:
        return f"mode:{binding.mode}"
    if binding.scope == "buffer" and binding.buffer:
        return f"buffer:{binding.buffer}"
    return binding.scope


def _show_help(editor: Editor, text: str) -> None:
    editor.state.buffers[HELP_BUFFER_NAME] = text
    editor.state.mark_buffer_recent(HELP_BUFFER_NAME)
    editor.pop_to_buffer(HELP_BUFFER_NAME, prefer_other=True)
