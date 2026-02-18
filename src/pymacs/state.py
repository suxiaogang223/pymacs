"""Core state model for PyMACS."""

from __future__ import annotations

from dataclasses import dataclass, field

from .keymap import KeySequence

LayoutRef = tuple[str, int]


@dataclass
class Window:
    """Leaf window in the layout tree."""

    id: int
    buffer: str


@dataclass
class SplitNode:
    """Binary split node in the layout tree."""

    id: int
    axis: str  # below | right
    first: LayoutRef
    second: LayoutRef


@dataclass
class EditorState:
    """Runtime mutable editor state."""

    buffers: dict[str, str] = field(default_factory=lambda: {"*scratch*": ""})
    variables: dict[str, object] = field(default_factory=dict)
    global_keymap: dict[KeySequence, str] = field(default_factory=dict)
    buffer_keymaps: dict[str, dict[KeySequence, str]] = field(default_factory=dict)
    mode_keymaps: dict[str, dict[KeySequence, str]] = field(default_factory=dict)
    buffer_modes: dict[str, list[str]] = field(default_factory=dict)

    windows: dict[int, Window] = field(default_factory=lambda: {1: Window(id=1, buffer="*scratch*")})
    splits: dict[int, SplitNode] = field(default_factory=dict)
    layout_root: LayoutRef = ("window", 1)
    selected_window_id: int = 1

    next_window_id: int = 2
    next_split_id: int = 1

    window_points: dict[int, dict[str, int]] = field(default_factory=lambda: {1: {"*scratch*": 0}})
    buffer_history: list[str] = field(default_factory=lambda: ["*scratch*"])

    def selected_buffer(self) -> str:
        window = self.windows[self.selected_window_id]
        self.ensure_buffer(window.buffer)
        self._ensure_window_point(window.id, window.buffer)
        return window.buffer

    def set_selected_buffer(self, buffer_name: str) -> None:
        self.set_window_buffer(self.selected_window_id, buffer_name)

    def current_text(self) -> str:
        buffer_name = self.selected_buffer()
        return self.buffers.setdefault(buffer_name, "")

    def set_current_text(self, text: str) -> None:
        buffer_name = self.selected_buffer()
        self.buffers[buffer_name] = text
        text_len = len(text)

        for points in self.window_points.values():
            if buffer_name not in points:
                continue
            points[buffer_name] = max(0, min(points[buffer_name], text_len))

    def current_cursor(self) -> int:
        return self.window_cursor(self.selected_window_id)

    def set_current_cursor(self, cursor: int) -> None:
        self.set_window_cursor(self.selected_window_id, cursor)

    def current_modes(self) -> list[str]:
        return list(self.buffer_modes.get(self.selected_buffer(), []))

    def window_list(self) -> list[int]:
        return self._walk_windows(self.layout_root)

    def layout_tree(self) -> tuple[object, ...]:
        return self._build_layout_tree(self.layout_root)

    def window_buffer(self, window_id: int) -> str:
        window = self.windows[window_id]
        self.ensure_buffer(window.buffer)
        return window.buffer

    def set_window_buffer(self, window_id: int, buffer_name: str) -> None:
        self.ensure_buffer(buffer_name)
        self.windows[window_id].buffer = buffer_name
        self._ensure_window_point(window_id, buffer_name)
        self.mark_buffer_recent(buffer_name)

    def window_cursor(self, window_id: int) -> int:
        buffer_name = self.window_buffer(window_id)
        return self._window_point(window_id, buffer_name)

    def set_window_cursor(self, window_id: int, cursor: int) -> None:
        buffer_name = self.window_buffer(window_id)
        text_len = len(self.buffers[buffer_name])
        self.window_points.setdefault(window_id, {})[buffer_name] = max(0, min(cursor, text_len))

    def split_selected_window(self, axis: str) -> int:
        if axis not in {"below", "right"}:
            raise ValueError(f"unknown split axis: {axis}")

        selected_id = self.selected_window_id
        selected_ref: LayoutRef = ("window", selected_id)
        selected_buffer = self.selected_buffer()
        selected_point = self.window_cursor(selected_id)

        new_window_id = self._allocate_window_id()
        self.windows[new_window_id] = Window(id=new_window_id, buffer=selected_buffer)
        self.window_points[new_window_id] = {selected_buffer: selected_point}

        split_id = self._allocate_split_id()
        split_ref: LayoutRef = ("split", split_id)
        self.splits[split_id] = SplitNode(
            id=split_id,
            axis=axis,
            first=selected_ref,
            second=("window", new_window_id),
        )

        self.layout_root = self._replace_ref(self.layout_root, selected_ref, split_ref)
        return new_window_id

    def other_window(self) -> int:
        windows = self.window_list()
        if len(windows) <= 1:
            return self.selected_window_id

        idx = windows.index(self.selected_window_id)
        self.selected_window_id = windows[(idx + 1) % len(windows)]
        return self.selected_window_id

    def delete_window(self) -> int:
        windows = self.window_list()
        if len(windows) <= 1:
            raise ValueError("cannot delete the only window")

        selected = self.selected_window_id
        target_ref: LayoutRef = ("window", selected)
        parent = self._find_parent(self.layout_root, target_ref)
        if parent is None:
            raise RuntimeError("cannot resolve parent split for selected window")

        parent_id, side = parent
        parent_ref: LayoutRef = ("split", parent_id)
        parent_node = self.splits[parent_id]
        sibling_ref = parent_node.second if side == "first" else parent_node.first

        self.layout_root = self._replace_ref(self.layout_root, parent_ref, sibling_ref)

        del self.windows[selected]
        self.window_points.pop(selected, None)
        del self.splits[parent_id]

        self.selected_window_id = self._first_window(sibling_ref)
        return self.selected_window_id

    def delete_other_windows(self) -> int:
        selected = self.selected_window_id
        selected_window = self.windows[selected]
        selected_points = self.window_points.get(selected, {})

        self.windows = {selected: selected_window}
        self.window_points = {selected: dict(selected_points)}
        self.splits = {}
        self.layout_root = ("window", selected)
        self._ensure_window_point(selected, selected_window.buffer)
        return selected

    def pop_to_buffer(self, buffer_name: str, *, prefer_other: bool = True) -> int:
        target_window_id = self.selected_window_id

        if prefer_other:
            for window_id in self.window_list():
                if window_id != self.selected_window_id:
                    target_window_id = window_id
                    break

        self.set_window_buffer(target_window_id, buffer_name)
        return target_window_id

    def ensure_buffer(self, buffer_name: str) -> None:
        if buffer_name not in self.buffers:
            self.buffers[buffer_name] = ""

    def mark_buffer_recent(self, buffer_name: str) -> None:
        self.ensure_buffer(buffer_name)
        self.buffer_history = [item for item in self.buffer_history if item != buffer_name]
        self.buffer_history.insert(0, buffer_name)

    def recent_buffer(self, *, exclude: set[str] | None = None) -> str | None:
        excluded = exclude or set()

        for name in self.buffer_history:
            if name in excluded:
                continue
            if name in self.buffers:
                return name

        for name in self.buffers:
            if name in excluded:
                continue
            return name

        return None

    def kill_buffer(self, buffer_name: str) -> str:
        if buffer_name not in self.buffers:
            raise KeyError(f"unknown buffer: {buffer_name}")

        del self.buffers[buffer_name]
        self.buffer_keymaps.pop(buffer_name, None)
        self.buffer_modes.pop(buffer_name, None)
        self.buffer_history = [name for name in self.buffer_history if name != buffer_name]

        for points in self.window_points.values():
            points.pop(buffer_name, None)

        replacement = self.recent_buffer(exclude={buffer_name})
        if replacement is None:
            replacement = "*scratch*"
            self.ensure_buffer(replacement)

        for window in self.windows.values():
            if window.buffer == buffer_name:
                window.buffer = replacement
                self._ensure_window_point(window.id, replacement)

        self.mark_buffer_recent(replacement)
        return replacement

    def _walk_windows(self, ref: LayoutRef) -> list[int]:
        kind, node_id = ref
        if kind == "window":
            return [node_id]

        split = self.splits[node_id]
        return [*self._walk_windows(split.first), *self._walk_windows(split.second)]

    def _build_layout_tree(self, ref: LayoutRef) -> tuple[object, ...]:
        kind, node_id = ref
        if kind == "window":
            return ("window", node_id)

        split = self.splits[node_id]
        return (
            "split",
            split.axis,
            self._build_layout_tree(split.first),
            self._build_layout_tree(split.second),
        )

    def _replace_ref(self, ref: LayoutRef, target: LayoutRef, replacement: LayoutRef) -> LayoutRef:
        if ref == target:
            return replacement

        kind, node_id = ref
        if kind == "window":
            return ref

        split = self.splits[node_id]
        split.first = self._replace_ref(split.first, target, replacement)
        split.second = self._replace_ref(split.second, target, replacement)
        return ref

    def _find_parent(
        self,
        ref: LayoutRef,
        target: LayoutRef,
        parent_id: int | None = None,
        side: str | None = None,
    ) -> tuple[int, str] | None:
        if ref == target:
            if parent_id is None or side is None:
                return None
            return parent_id, side

        kind, node_id = ref
        if kind == "window":
            return None

        split = self.splits[node_id]
        found = self._find_parent(split.first, target, node_id, "first")
        if found is not None:
            return found

        return self._find_parent(split.second, target, node_id, "second")

    def _first_window(self, ref: LayoutRef) -> int:
        kind, node_id = ref
        if kind == "window":
            return node_id

        split = self.splits[node_id]
        return self._first_window(split.first)

    def _window_point(self, window_id: int, buffer_name: str) -> int:
        self._ensure_window_point(window_id, buffer_name)
        point = self.window_points[window_id][buffer_name]
        text_len = len(self.buffers[buffer_name])
        clamped = max(0, min(point, text_len))
        self.window_points[window_id][buffer_name] = clamped
        return clamped

    def _ensure_window_point(self, window_id: int, buffer_name: str) -> None:
        self.ensure_buffer(buffer_name)
        points = self.window_points.setdefault(window_id, {})
        points.setdefault(buffer_name, 0)

    def _allocate_window_id(self) -> int:
        window_id = self.next_window_id
        self.next_window_id += 1
        return window_id

    def _allocate_split_id(self) -> int:
        split_id = self.next_split_id
        self.next_split_id += 1
        return split_id
