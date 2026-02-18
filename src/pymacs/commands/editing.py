"""Built-in editing and state commands."""

from __future__ import annotations

from ..core import Editor

BUFFER_LIST_NAME = "*Buffer List*"


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

    def switch_to_buffer(ed: Editor, name: str) -> None:
        """Switch selected window to buffer NAME, creating buffer if needed."""
        target = str(name).strip()
        if not target:
            raise ValueError("usage: switch-to-buffer <name>")
        ed.state.set_selected_buffer(target)

    def list_buffers(ed: Editor) -> str:
        """Show a read-only list of buffers."""
        lines = ["Buffers", "", "* marks current buffer", ""]
        current = ed.state.selected_buffer()
        for name in sorted(ed.state.buffers):
            marker = "*" if name == current else " "
            lines.append(f"{marker} {name:<20} {len(ed.state.buffers[name])} chars")

        ed.state.buffers[BUFFER_LIST_NAME] = "\n".join(lines)
        ed.state.mark_buffer_recent(BUFFER_LIST_NAME)
        ed.pop_to_buffer(BUFFER_LIST_NAME, prefer_other=True)
        return "buffer list"

    def kill_buffer(ed: Editor, *parts: object) -> str:
        """Kill buffer NAME, or current buffer when NAME is omitted."""
        target = " ".join(str(part) for part in parts).strip() or ed.state.selected_buffer()
        replacement = ed.state.kill_buffer(target)
        return f"killed {target} -> {replacement}"

    def split_window_below(ed: Editor) -> None:
        """Split selected window into upper/lower windows."""
        ed.split_window_below()

    def split_window_right(ed: Editor) -> None:
        """Split selected window into left/right windows."""
        ed.split_window_right()

    def other_window(ed: Editor) -> None:
        """Select the next window in layout traversal order."""
        ed.other_window()

    def delete_window(ed: Editor) -> None:
        """Delete the selected window."""
        ed.delete_window()

    def delete_other_windows(ed: Editor) -> None:
        """Delete all windows except the selected one."""
        ed.delete_other_windows()

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
        """Return selected window buffer contents."""
        return ed.state.current_text()

    def set_var(ed: Editor, key: str, *value: object) -> None:
        """Set variable KEY to joined VALUE parts."""
        ed.state.variables[key] = " ".join(str(v) for v in value)

    def get_var(ed: Editor, key: str) -> object:
        """Get variable KEY from editor state."""
        return ed.state.variables.get(key)

    editor.command("switch-to-buffer", switch_to_buffer, source_kind="builtin")
    editor.command("list-buffers", list_buffers, source_kind="builtin")
    editor.command("kill-buffer", kill_buffer, source_kind="builtin")

    editor.command("split-window-below", split_window_below, source_kind="builtin")
    editor.command("split-window-right", split_window_right, source_kind="builtin")
    editor.command("other-window", other_window, source_kind="builtin")
    editor.command("delete-window", delete_window, source_kind="builtin")
    editor.command("delete-other-windows", delete_other_windows, source_kind="builtin")

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
