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
- `C-d` / `DEL`: delete forward/backward char
- `C-k`: kill line
- `M-x`: minibuffer command input
- `C-x 2` / `C-x 3`: split window below/right
- `C-x o`: switch to other window
- `C-x 0` / `C-x 1`: delete selected/other windows
- `C-x b`: switch to buffer
- `C-x C-b`: show buffer list
- `C-x k`: kill buffer
- `C-h f`: describe command
- `C-h k`: describe key
- `C-h w`: where-is (find bindings for command)
- `C-x C-c` or `C-q`: quit

## Multi-Window and Multi-Buffer

PyMACS now uses an Emacs-style multi-window model:

1. Window layout is a binary split tree (`C-x 2` / `C-x 3`).
2. The selected window moves with `C-x o`.
3. Each window remembers point per buffer (`window + buffer` memory).
4. Help and buffer-list output prefer another window when one exists.
5. Current scope is **single frame only** (no multi-frame support yet).

Buffer management follows Emacs command naming:

1. `switch-to-buffer`
2. `list-buffers`
3. `kill-buffer`

## Runtime Layers

PyMACS TUI now uses a strict three-layer boundary:

1. Core (`src/pymacs/core.py`, `src/pymacs/state.py`): command bus, keymap resolution, mutable editor state.
2. UI Controller (`src/pymacs/ui/controller.py`): translates UI events into editor commands and exposes immutable render snapshots.
3. Textual App (`src/pymacs/ui/app.py`): widgets, focus, rendering, and platform event handling.

The Textual App does not read `EditorState` directly. Rendering data comes from `UIController.snapshot()`.

## Command Metadata and Help

PyMACS commands are self-documenting by default:

1. `Editor.command(name, fn)` stores command metadata at registration time.
2. Metadata includes command docstring, Python signature, module, and source kind (`builtin` / `plugin` / `runtime`).
3. Plugins loaded from `~/.pymacs/init.py` or explicit plugin files automatically register commands as `plugin` source.

Help commands render to `*Help*` buffer:

1. `describe-command`
2. `describe-key`
3. `where-is`

Use `C-h` as the help prefix in TUI for interactive help prompts.

For source-only development (without install):

```bash
cd /Users/xiaogangsu/code/pymacs
PYTHONPATH=src python3 -m pymacs.main
```

## Config

1. Config directory: `~/.pymacs`
2. Init file: `~/.pymacs/init.py`
