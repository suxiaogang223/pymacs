"""PyMACS package."""

__all__ = ["Editor", "EditorState", "parse_key_sequence"]
__version__ = "0.1.0"

from .core import Editor
from .keymap import parse_key_sequence
from .state import EditorState
