"""Core state model for PyMACS."""

from dataclasses import dataclass, field

from .keymap import KeySequence


@dataclass
class EditorState:
    """Runtime mutable editor state."""

    buffers: dict[str, str] = field(default_factory=lambda: {"*scratch*": ""})
    cursors: dict[str, int] = field(default_factory=lambda: {"*scratch*": 0})
    current_buffer: str = "*scratch*"
    variables: dict[str, object] = field(default_factory=dict)
    global_keymap: dict[KeySequence, str] = field(default_factory=dict)
    buffer_keymaps: dict[str, dict[KeySequence, str]] = field(default_factory=dict)
    mode_keymaps: dict[str, dict[KeySequence, str]] = field(default_factory=dict)
    buffer_modes: dict[str, list[str]] = field(default_factory=dict)

    def current_text(self) -> str:
        text = self.buffers.setdefault(self.current_buffer, "")
        self.cursors.setdefault(self.current_buffer, min(len(text), self.cursors.get(self.current_buffer, 0)))
        return text

    def set_current_text(self, text: str) -> None:
        self.buffers[self.current_buffer] = text
        self.set_current_cursor(self.current_cursor())

    def current_cursor(self) -> int:
        text = self.current_text()
        cursor = self.cursors.setdefault(self.current_buffer, 0)
        return max(0, min(cursor, len(text)))

    def set_current_cursor(self, cursor: int) -> None:
        text_len = len(self.current_text())
        self.cursors[self.current_buffer] = max(0, min(cursor, text_len))

    def current_modes(self) -> list[str]:
        return list(self.buffer_modes.get(self.current_buffer, []))
