"""Core state model for PyMACS."""

from dataclasses import dataclass, field

from .keymap import KeySequence


@dataclass
class EditorState:
    """Runtime mutable editor state."""

    buffers: dict[str, str] = field(default_factory=lambda: {"*scratch*": ""})
    current_buffer: str = "*scratch*"
    variables: dict[str, object] = field(default_factory=dict)
    global_keymap: dict[KeySequence, str] = field(default_factory=dict)
    buffer_keymaps: dict[str, dict[KeySequence, str]] = field(default_factory=dict)
    mode_keymaps: dict[str, dict[KeySequence, str]] = field(default_factory=dict)
    buffer_modes: dict[str, list[str]] = field(default_factory=dict)

    def current_text(self) -> str:
        return self.buffers.setdefault(self.current_buffer, "")

    def set_current_text(self, text: str) -> None:
        self.buffers[self.current_buffer] = text

    def current_modes(self) -> list[str]:
        return list(self.buffer_modes.get(self.current_buffer, []))
