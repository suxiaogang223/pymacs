from __future__ import annotations

from pymacs import cli


def _run_shell(monkeypatch, capsys, inputs: list[str]) -> str:
    data = iter(inputs)
    monkeypatch.setattr("builtins.input", lambda _prompt: next(data))
    cli.main()
    return capsys.readouterr().out


def test_shell_help_and_quit(monkeypatch, capsys) -> None:
    out = _run_shell(monkeypatch, capsys, [":help", ":quit"])
    assert "PyMACS shell. Type: :help" in out
    assert ":run <cmd> [args...]" in out


def test_shell_run_with_quoted_args(monkeypatch, capsys) -> None:
    out = _run_shell(
        monkeypatch,
        capsys,
        [
            ":run new-buffer notes",
            ":run switch-buffer notes",
            ':run insert "hello world"',
            ":run show-buffer",
            ":quit",
        ],
    )
    assert "hello world" in out


def test_shell_error_paths(monkeypatch, capsys) -> None:
    out = _run_shell(
        monkeypatch,
        capsys,
        [
            ":run",
            ":run missing",
            ':run insert "unterminated',
            ":eval",
            ":eval 1/0",
            ":quit",
        ],
    )
    assert "usage: :run <cmd> [args...]" in out
    assert "unknown command: missing" in out
    assert "parse error:" in out
    assert "usage: :eval <python>" in out
    assert "eval error:" in out


def test_shell_lists_commands(monkeypatch, capsys) -> None:
    out = _run_shell(monkeypatch, capsys, [":commands", ":quit"])
    assert "new-buffer" in out
    assert "show-buffer" in out


def test_shell_handles_unknown_input(monkeypatch, capsys) -> None:
    out = _run_shell(monkeypatch, capsys, ["not-a-command", ":quit"])
    assert "unknown input. use :help" in out


def test_shell_ignores_empty_input(monkeypatch, capsys) -> None:
    out = _run_shell(monkeypatch, capsys, ["", ":quit"])
    assert "unknown input. use :help" not in out


def test_shell_eval_success_path(monkeypatch, capsys) -> None:
    out = _run_shell(
        monkeypatch,
        capsys,
        [
            ":eval editor.run('new-buffer', 'tmp')",
            ":eval editor.run('switch-buffer', 'tmp')",
            ":run insert hi",
            ":run show-buffer",
            ":buf",
            ":quit",
        ],
    )
    assert "hi" in out
    assert "tmp" in out


def test_shell_exits_on_eof(monkeypatch, capsys) -> None:
    def _raise_eof(_prompt: str) -> str:
        raise EOFError

    monkeypatch.setattr("builtins.input", _raise_eof)
    cli.main()
    out = capsys.readouterr().out
    assert "PyMACS shell. Type: :help" in out


def test_shell_exits_on_keyboard_interrupt(monkeypatch, capsys) -> None:
    def _raise_interrupt(_prompt: str) -> str:
        raise KeyboardInterrupt

    monkeypatch.setattr("builtins.input", _raise_interrupt)
    cli.main()
    out = capsys.readouterr().out
    assert "PyMACS shell. Type: :help" in out
