import pytest

from pymacs import main as main_module


def test_main_dispatches_to_tui_by_default(monkeypatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(main_module, "run_tui", lambda: calls.append("tui"))

    main_module.main([])

    assert calls == ["tui"]


def test_main_rejects_removed_shell_flag() -> None:
    with pytest.raises(SystemExit):
        main_module.main(["--shell"])
