"""Built-in command registration shared by shell and UI."""

from __future__ import annotations

from .core import Editor


def register_builtin_commands(editor: Editor) -> None:
    """Register core editing commands on an editor instance."""

    def new_buffer(ed: Editor, name: str) -> None:
        ed.state.buffers.setdefault(name, "")

    def switch_buffer(ed: Editor, name: str) -> None:
        if name not in ed.state.buffers:
            ed.state.buffers[name] = ""
        ed.state.current_buffer = name

    def insert(ed: Editor, *parts: object) -> None:
        text = " ".join(str(p) for p in parts)
        ed.state.set_current_text(ed.state.current_text() + text)

    def show_buffer(ed: Editor) -> str:
        return ed.state.current_text()

    def set_var(ed: Editor, key: str, *value: object) -> None:
        ed.state.variables[key] = " ".join(str(v) for v in value)

    def get_var(ed: Editor, key: str) -> object:
        return ed.state.variables.get(key)

    editor.command("new-buffer", new_buffer)
    editor.command("switch-buffer", switch_buffer)
    editor.command("insert", insert)
    editor.command("show-buffer", show_buffer)
    editor.command("set", set_var)
    editor.command("get", get_var)
