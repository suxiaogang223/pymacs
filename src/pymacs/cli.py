"""Minimal interactive shell for PyMACS."""

from __future__ import annotations

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

        if not raw:
            continue
        if raw in {":q", ":quit", ":exit"}:
            break
        if raw == ":help":
            print("Commands:")
            print("  :commands                list command names")
            print("  :buf                     show current buffer name")
            print("  :run <cmd> [args...]     run command")
            print("  :eval <python>           exec python with variable 'editor'")
            print("  :quit                    exit shell")
            continue
        if raw == ":commands":
            for name in editor.commands:
                print(name)
            continue
        if raw == ":buf":
            print(editor.state.current_buffer)
            continue
        if raw.startswith(":eval "):
            code = raw[len(":eval ") :]
            exec(code, {}, {"editor": editor})
            continue
        if raw.startswith(":run "):
            parts = raw[len(":run ") :].split()
            name, args = parts[0], parts[1:]
            result = editor.run(name, *args)
            if result is not None:
                print(result)
            continue

        print("unknown input. use :help")


if __name__ == "__main__":
    main()
