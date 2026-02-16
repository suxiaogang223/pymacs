# PyMACS Implementation Document

## 1. Scope

PyMACS is focused on Emacs-style dynamic extensibility rather than full feature parity.
The first milestone delivers a programmable editor kernel.

## 2. Design Principles

1. Runtime-first: editor behavior is mutable while running.
2. Python-native: config and plugins are Python code.
3. Small trusted core: state, command bus, hook bus, plugin loader.
4. Incremental delivery: kernel -> shell -> text UI/GUI.

## 3. Core Runtime Architecture

### 3.1 EditorState

Single source of truth:

1. Buffers and current buffer.
2. Cursor positions.
3. Editor variables/options.
4. Future: windows, frames, keymaps.

### 3.2 Command Bus

1. Register command by name.
2. Execute command by name + args.
3. Command signatures always receive `Editor` as first argument.
4. Future: command metadata and undo grouping.

### 3.3 Hook Bus

1. Register multiple callbacks per event.
2. Emit lifecycle events (`before-command`, `after-command`, etc.).
3. Isolate hook failures (log and continue).

### 3.4 Plugin Loader

1. Load Python module from path.
2. Convention: plugin exposes `activate(editor)`.
3. Maintain loaded plugin registry.
4. Future: deactivate/reload lifecycle.

### 3.5 Eval Interface

1. Evaluate runtime code with access to editor object.
2. Use controlled global/local scopes.
3. Future: safe mode and capability boundaries.

## 4. Milestones

### M1: Kernel (current)

1. `EditorState` with buffers/options.
2. Command registration/execution.
3. Hook registration/emission.
4. Plugin file loading.

### M2: Interactive Shell

1. Minimal REPL loop.
2. Built-in commands:
   - `new-buffer`
   - `switch-buffer`
   - `insert`
   - `show-buffer`
   - `set`
   - `get`

### M3: Keymap and Input Model

1. Key sequence parser.
2. Keymap layering (global + buffer-local + mode-local).
3. `command-execute` path.

### M4: UI Layer

1. TUI prototype (Textual) first.
2. Optional GUI path (PySide6).
3. Rendering separated from editor core.

## 5. Extension Contract (v0)

A plugin must implement:

```python
def activate(editor):
    ...
```

Plugin can call:

1. `editor.command(name, fn)`
2. `editor.on(event, fn)`
3. `editor.state` mutations

## 6. Risks and Controls

1. Plugin safety risk:
   - Control: trusted plugin model in v0, sandbox later.
2. Performance risk:
   - Control: keep core data structures simple, profile before optimizing.
3. Scope creep:
   - Control: deliver kernel API before advanced features.

## 7. Initial Directory Layout

```text
pymacs/
  IMPLEMENTATION.md
  README.md
  pyproject.toml
  src/
    pymacs/
      __init__.py
      state.py
      core.py
      cli.py
```

