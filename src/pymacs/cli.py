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
    print("  :bind <key> <cmd> [scope] bind key (scope: global|buffer|mode:<name>)")
    print("  :press <key> [args...]   execute key sequence")
    print("  :mode <name> [on|off]    enable/disable mode on current buffer")
    print("  :modes                   list enabled modes for current buffer")
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


def _bind_key(editor: Editor, payload: str) -> None:
    try:
        parts = shlex.split(payload)
    except ValueError as exc:
        print(f"parse error: {exc}")
        return

    if len(parts) < 2:
        print("usage: :bind <key> <cmd> [global|buffer|mode:<name>]")
        return

    key, command_name = parts[0], parts[1]
    scope_spec = parts[2] if len(parts) >= 3 else "global"

    try:
        if scope_spec == "global":
            editor.bind_key(key, command_name, scope="global")
            print(f"bound {key} -> {command_name} (global)")
            return
        if scope_spec == "buffer":
            editor.bind_key(key, command_name, scope="buffer")
            print(f"bound {key} -> {command_name} (buffer:{editor.state.current_buffer})")
            return
        if scope_spec.startswith("mode:"):
            mode = scope_spec.split(":", 1)[1]
            if not mode:
                print("usage: :bind <key> <cmd> [global|buffer|mode:<name>]")
                return
            editor.bind_key(key, command_name, scope="mode", mode=mode)
            print(f"bound {key} -> {command_name} (mode:{mode})")
            return
        print("usage: :bind <key> <cmd> [global|buffer|mode:<name>]")
    except KeyError as exc:
        print(exc.args[0])
    except ValueError as exc:
        print(exc)


def _press_key(editor: Editor, payload: str) -> None:
    try:
        parts = shlex.split(payload)
    except ValueError as exc:
        print(f"parse error: {exc}")
        return

    if not parts:
        print("usage: :press <key> [args...]")
        return

    key, args = parts[0], parts[1:]
    try:
        result = editor.command_execute(key, *args)
    except KeyError as exc:
        print(exc.args[0])
        return
    except Exception as exc:
        print(f"command error: {exc}")
        return

    if result is not None:
        print(result)


def _set_mode(editor: Editor, payload: str) -> None:
    try:
        parts = shlex.split(payload)
    except ValueError as exc:
        print(f"parse error: {exc}")
        return

    if not parts:
        print("usage: :mode <name> [on|off]")
        return

    name = parts[0]
    action = parts[1] if len(parts) >= 2 else "on"

    if action == "on":
        editor.enable_mode(name)
    elif action == "off":
        editor.disable_mode(name)
    else:
        print("usage: :mode <name> [on|off]")
        return

    print(f"mode {name}: {action}")


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
    if raw == ":bind":
        print("usage: :bind <key> <cmd> [global|buffer|mode:<name>]")
        return True
    if raw.startswith(":bind "):
        _bind_key(editor, raw[len(":bind ") :])
        return True
    if raw == ":press":
        print("usage: :press <key> [args...]")
        return True
    if raw.startswith(":press "):
        _press_key(editor, raw[len(":press ") :])
        return True
    if raw == ":modes":
        for mode in editor.state.current_modes():
            print(mode)
        return True
    if raw == ":mode":
        print("usage: :mode <name> [on|off]")
        return True
    if raw.startswith(":mode "):
        _set_mode(editor, raw[len(":mode ") :])
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
