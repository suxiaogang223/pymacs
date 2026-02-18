"""Top-level CLI entrypoint dispatcher."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from .tui import run_tui


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="pymacs")
    parser.parse_args(argv)
    run_tui()
