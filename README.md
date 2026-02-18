# PyMACS

PyMACS = **Py**thon **M**odular **A**daptive **C**ommand **S**ystem

PyMACS is an Emacs-style programmable editor core implemented in Python.
The core target is runtime extensibility:

1. Live mutable editor state machine.
2. Runtime command/hook/plugin extension.
3. Python as both implementation and configuration language.

## Quick Start

```bash
cd /Users/xiaogangsu/code/pymacs
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
pymacs
```

`pymacs` now starts the Textual TUI by default.

- `M-x`: open minibuffer command input
- `C-g` or `Esc`: cancel minibuffer
- `C-q`: quit TUI

## Keybinding Principle

PyMACS follows an Emacs-first keybinding strategy. Default key behavior is designed to stay as close as practical to Emacs so existing Emacs users can use PyMACS with minimal relearning.

Current default bindings include:

- `C-f` / `C-b`: forward/backward char
- `C-a` / `C-e`: beginning/end of line
- `C-n` / `C-p`: next/previous line
- `C-d` / `C-h`: delete forward/backward char
- `C-k`: kill line
- `M-x`: minibuffer command input
- `C-x C-c` or `C-q`: quit

## Runtime Layers

PyMACS TUI now uses a strict three-layer boundary:

1. Core (`src/pymacs/core.py`, `src/pymacs/state.py`): command bus, keymap resolution, mutable editor state.
2. UI Controller (`src/pymacs/ui/controller.py`): translates UI events into editor commands and exposes immutable render snapshots.
3. Textual App (`src/pymacs/ui/app.py`): widgets, focus, rendering, and platform event handling.

The Textual App does not read `EditorState` directly. Rendering data comes from `UIController.snapshot()`.

For source-only development (without install):

```bash
cd /Users/xiaogangsu/code/pymacs
PYTHONPATH=src python3 -m pymacs.main
```

## Config

1. Config directory: `~/.pymacs`
2. Init file: `~/.pymacs/init.py`
