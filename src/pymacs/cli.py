"""Minimal interactive shell for PyMACS."""

from __future__ import annotations

import shlex

from .core import Editor


def _register_builtin_commands(editor: Editor) -> None:
    def new_buffer(ed: Editor, name: str) -> None:
        ed.state.buffers.setdefault(name, "")

    def switch_buffer(ed: Editor, name: str) -> None:
        if name not in ed.state.buffers:
            ed.state.buffers[name] = ""
        ed.state.current_buffer = name

    def insert(ed: Editor, *parts: object) -> None:
        text = " ".join(str(p) for p in parts)
        ed.state.set_current_text(ed.state.current_text() + text)

    def show_buffer(ed: Editor) -> str:
        return ed.state.current_text()

    def set_var(ed: Editor, key: str, *value: object) -> None:
        ed.state.variables[key] = " ".join(str(v) for v in value)

    def get_var(ed: Editor, key: str) -> object:
        return ed.state.variables.get(key)

    editor.command("new-buffer", new_buffer)
    editor.command("switch-buffer", switch_buffer)
    editor.command("insert", insert)
    editor.command("show-buffer", show_buffer)
    editor.command("set", set_var)
    editor.command("get", get_var)


def _print_help() -> None:
    print("Commands:")
    print("  :commands                list command names")
    print("  :buf                     show current buffer name")
    print("  :run <cmd> [args...]     run command")
    print("  :eval <python>           exec python with variable 'editor'")
    print("  :quit                    exit shell")


def _run_command(editor: Editor, payload: str) -> None:
    try:
        parts = shlex.split(payload)
    except ValueError as exc:
        print(f"parse error: {exc}")
        return

    if not parts:
        print("usage: :run <cmd> [args...]")
        return

    name, args = parts[0], parts[1:]
    try:
        result = editor.run(name, *args)
    except KeyError as exc:
        print(exc.args[0])
        return
    except Exception as exc:
        print(f"command error: {exc}")
        return

    if result is not None:
        print(result)


def _eval_code(editor: Editor, payload: str) -> None:
    try:
        exec(payload, {}, {"editor": editor})
    except Exception as exc:
        print(f"eval error: {exc}")


def _handle_input(editor: Editor, raw: str) -> bool:
    if not raw:
        return True
    if raw in {":q", ":quit", ":exit"}:
        return False
    if raw == ":help":
        _print_help()
        return True
    if raw == ":commands":
        for name in editor.commands:
            print(name)
        return True
    if raw == ":buf":
        print(editor.state.current_buffer)
        return True
    if raw == ":run":
        print("usage: :run <cmd> [args...]")
        return True
    if raw.startswith(":run "):
        _run_command(editor, raw[len(":run ") :])
        return True
    if raw == ":eval":
        print("usage: :eval <python>")
        return True
    if raw.startswith(":eval "):
        _eval_code(editor, raw[len(":eval ") :])
        return True

    print("unknown input. use :help")
    return True


def main() -> None:
    editor = Editor()
    _register_builtin_commands(editor)

    print("PyMACS shell. Type: :help")
    while True:
        try:
            raw = input("pymacs> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not _handle_input(editor, raw):
            break


if __name__ == "__main__":
    main()
