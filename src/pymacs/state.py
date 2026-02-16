"""Core state model for PyMACS."""

from dataclasses import dataclass, field


@dataclass
class EditorState:
    """Runtime mutable editor state."""

    buffers: dict[str, str] = field(default_factory=lambda: {"*scratch*": ""})
    current_buffer: str = "*scratch*"
    variables: dict[str, object] = field(default_factory=dict)

    def current_text(self) -> str:
        return self.buffers.setdefault(self.current_buffer, "")

    def set_current_text(self, text: str) -> None:
        self.buffers[self.current_buffer] = text
