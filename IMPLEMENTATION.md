# PyMACS Implementation Document

## 1. Scope

PyMACS is focused on Emacs-style dynamic extensibility rather than full feature parity.
The first milestone delivers a programmable editor kernel.

## 2. Design Principles

1. Runtime-first: editor behavior is mutable while running.
2. Python-native: config and plugins are Python code.
3. Small trusted core: state, command bus, hook bus, plugin loader.
4. Incremental delivery: kernel -> text UI -> optional GUI.
5. Emacs-first keybindings: default key behavior should follow Emacs conventions so Emacs users can onboard with minimal relearning.

## 3. Core Runtime Architecture

### 3.1 EditorState

Single source of truth:

1. Buffers and window layout tree.
2. Selected window and per-window point state.
3. Editor variables/options.
4. Future: frames and more advanced window management.

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

### M1: Kernel (done)

1. `EditorState` with buffers/options.
2. Command registration/execution.
3. Hook registration/emission.
4. Plugin file loading.

### M2: Interactive Shell (retired)

1. A minimal REPL shell was delivered as an early development interface.
2. It has been removed in favor of a single default TUI entrypoint in M4.

### M3: Keymap and Input Model (done)

1. Key sequence parser.
2. Keymap layering (global + buffer-local + mode-local).
3. `command_execute` path.
4. Compatibility target: prioritize Emacs-style default keybindings and interaction patterns.

### M4: UI Layer (done)

1. Single default frontend is Textual TUI.
2. `UIController` is the only adapter between TUI events and editor core APIs.
3. Textual rendering reads immutable UI snapshots instead of touching `EditorState` directly.
4. Initial delivered scope was single-buffer TUI, status line, and minibuffer command input.

### M5: Command Metadata and Help System (done)

1. Commands are self-documenting via docstring + runtime introspection.
2. `Editor` exposes query APIs: command metadata, key description, and where-is lookup.
3. Built-in help commands: `describe-command`, `describe-key`, `where-is`.
4. Emacs-style help prefix in TUI: `C-h f`, `C-h k`, `C-h w`.
5. Python remains the extension language for user config and plugins.

### M6: Multi-Window and Multi-Buffer (current)

1. Editor state uses a window split tree instead of a single global current buffer.
2. Window commands are Emacs-aligned: split/select/delete window variants.
3. Buffer commands use Emacs naming: `switch-to-buffer`, `list-buffers`, `kill-buffer`.
4. Point memory is tracked by `window + buffer`.
5. TUI renders recursive panes with per-window local status lines.
6. Current implementation is single-frame only; multi-frame support is out of scope for M6.

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
      main.py
      state.py
      core.py
      keymap.py
      commands/
        __init__.py
        editing.py
        help.py
      tui.py
      ui/
        app.py
        controller.py
```
