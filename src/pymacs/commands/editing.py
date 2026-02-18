"""Built-in editing and state commands."""

from __future__ import annotations

from ..core import Editor


def register_editing_commands(editor: Editor) -> None:
    """Register core editing/state commands."""

    def _parse_count(parts: tuple[object, ...], default: int = 1) -> int:
        if not parts:
            return default
        try:
            return int(parts[0])
        except (TypeError, ValueError) as exc:
            raise ValueError("count must be an integer") from exc

    def _insert_text(ed: Editor, text: str) -> None:
        current = ed.state.current_text()
        cursor = ed.state.current_cursor()
        ed.state.set_current_text(current[:cursor] + text + current[cursor:])
        ed.state.set_current_cursor(cursor + len(text))

    def new_buffer(ed: Editor, name: str) -> None:
        """Create a buffer if it does not exist."""
        ed.state.buffers.setdefault(name, "")
        ed.state.cursors.setdefault(name, 0)

    def switch_buffer(ed: Editor, name: str) -> None:
        """Switch the current buffer to NAME, creating it if needed."""
        if name not in ed.state.buffers:
            ed.state.buffers[name] = ""
        ed.state.cursors.setdefault(name, len(ed.state.buffers[name]))
        ed.state.current_buffer = name

    def insert(ed: Editor, *parts: object) -> None:
        """Insert text at point."""
        text = " ".join(str(p) for p in parts)
        _insert_text(ed, text)

    def newline(ed: Editor) -> None:
        """Insert a newline at point."""
        _insert_text(ed, "\n")

    def forward_char(ed: Editor, *parts: object) -> None:
        """Move point forward by COUNT characters."""
        count = max(0, _parse_count(parts))
        ed.state.set_current_cursor(ed.state.current_cursor() + count)

    def backward_char(ed: Editor, *parts: object) -> None:
        """Move point backward by COUNT characters."""
        count = max(0, _parse_count(parts))
        ed.state.set_current_cursor(ed.state.current_cursor() - count)

    def move_beginning_of_line(ed: Editor) -> None:
        """Move point to beginning of current line."""
        text = ed.state.current_text()
        cursor = ed.state.current_cursor()
        start = text.rfind("\n", 0, cursor) + 1
        ed.state.set_current_cursor(start)

    def move_end_of_line(ed: Editor) -> None:
        """Move point to end of current line."""
        text = ed.state.current_text()
        cursor = ed.state.current_cursor()
        end = text.find("\n", cursor)
        if end == -1:
            end = len(text)
        ed.state.set_current_cursor(end)

    def next_line(ed: Editor) -> None:
        """Move point vertically to next line preserving column when possible."""
        text = ed.state.current_text()
        cursor = ed.state.current_cursor()
        line_start = text.rfind("\n", 0, cursor) + 1
        col = cursor - line_start
        current_end = text.find("\n", cursor)
        if current_end == -1:
            return
        next_start = current_end + 1
        next_end = text.find("\n", next_start)
        if next_end == -1:
            next_end = len(text)
        ed.state.set_current_cursor(min(next_start + col, next_end))

    def previous_line(ed: Editor) -> None:
        """Move point vertically to previous line preserving column when possible."""
        text = ed.state.current_text()
        cursor = ed.state.current_cursor()
        line_start = text.rfind("\n", 0, cursor) + 1
        col = cursor - line_start
        if line_start == 0:
            return
        prev_end = line_start - 1
        prev_start = text.rfind("\n", 0, prev_end) + 1
        ed.state.set_current_cursor(min(prev_start + col, prev_end))

    def delete_backward_char(ed: Editor, *parts: object) -> None:
        """Delete COUNT chars before point."""
        count = max(0, _parse_count(parts))
        if count == 0:
            return
        text = ed.state.current_text()
        cursor = ed.state.current_cursor()
        if cursor == 0:
            return
        start = max(0, cursor - count)
        ed.state.set_current_text(text[:start] + text[cursor:])
        ed.state.set_current_cursor(start)

    def delete_forward_char(ed: Editor, *parts: object) -> None:
        """Delete COUNT chars after point."""
        count = max(0, _parse_count(parts))
        if count == 0:
            return
        text = ed.state.current_text()
        cursor = ed.state.current_cursor()
        if cursor >= len(text):
            return
        end = min(len(text), cursor + count)
        ed.state.set_current_text(text[:cursor] + text[end:])
        ed.state.set_current_cursor(cursor)

    def kill_line(ed: Editor) -> None:
        """Kill text from point to end of line, or delete newline at EOL."""
        text = ed.state.current_text()
        cursor = ed.state.current_cursor()
        if cursor >= len(text):
            return
        line_end = text.find("\n", cursor)
        if line_end == -1:
            ed.state.set_current_text(text[:cursor])
            ed.state.set_current_cursor(cursor)
            return
        if line_end == cursor:
            ed.state.set_current_text(text[:cursor] + text[cursor + 1 :])
            ed.state.set_current_cursor(cursor)
            return
        ed.state.set_current_text(text[:cursor] + text[line_end:])
        ed.state.set_current_cursor(cursor)

    def show_buffer(ed: Editor) -> str:
        """Return current buffer contents."""
        return ed.state.current_text()

    def set_var(ed: Editor, key: str, *value: object) -> None:
        """Set variable KEY to joined VALUE parts."""
        ed.state.variables[key] = " ".join(str(v) for v in value)

    def get_var(ed: Editor, key: str) -> object:
        """Get variable KEY from editor state."""
        return ed.state.variables.get(key)

    editor.command("new-buffer", new_buffer, source_kind="builtin")
    editor.command("switch-buffer", switch_buffer, source_kind="builtin")
    editor.command("insert", insert, source_kind="builtin")
    editor.command("newline", newline, source_kind="builtin")
    editor.command("forward-char", forward_char, source_kind="builtin")
    editor.command("backward-char", backward_char, source_kind="builtin")
    editor.command("move-beginning-of-line", move_beginning_of_line, source_kind="builtin")
    editor.command("move-end-of-line", move_end_of_line, source_kind="builtin")
    editor.command("next-line", next_line, source_kind="builtin")
    editor.command("previous-line", previous_line, source_kind="builtin")
    editor.command("delete-backward-char", delete_backward_char, source_kind="builtin")
    editor.command("delete-forward-char", delete_forward_char, source_kind="builtin")
    editor.command("kill-line", kill_line, source_kind="builtin")
    editor.command("show-buffer", show_buffer, source_kind="builtin")
    editor.command("set", set_var, source_kind="builtin")
    editor.command("get", get_var, source_kind="builtin")
