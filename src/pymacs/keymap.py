"""Key sequence parsing helpers for input model."""

from __future__ import annotations

from collections.abc import Sequence

MODIFIER_ORDER = ("C", "M", "S")
MODIFIER_ALIASES = {
    "C": "C",
    "CTRL": "C",
    "CONTROL": "C",
    "M": "M",
    "META": "M",
    "ALT": "M",
    "S": "S",
    "SHIFT": "S",
}

KeySequence = tuple[str, ...]
KeySequenceInput = str | Sequence[str]


def parse_key_sequence(sequence: KeySequenceInput) -> KeySequence:
    """Parse user input into canonical key-sequence tuples."""
    tokens: list[str]
    if isinstance(sequence, str):
        tokens = sequence.split()
    else:
        tokens = [str(tok).strip() for tok in sequence]

    if not tokens:
        raise ValueError("empty key sequence")

    return tuple(_parse_chord(token) for token in tokens)


def format_key_sequence(sequence: KeySequence) -> str:
    """Render a canonical key sequence for messages."""
    return " ".join(sequence)


def _parse_chord(token: str) -> str:
    token = token.strip()
    if not token:
        raise ValueError("empty key token")

    parts = token.split("-")
    if any(part == "" for part in parts):
        raise ValueError(f"invalid key token: {token}")

    base = parts[-1]
    if not base:
        raise ValueError(f"missing key in token: {token}")

    modifiers: list[str] = []
    for raw_mod in parts[:-1]:
        mod = MODIFIER_ALIASES.get(raw_mod.upper())
        if mod is None:
            raise ValueError(f"unknown key modifier: {raw_mod}")
        if mod not in modifiers:
            modifiers.append(mod)

    ordered = [mod for mod in MODIFIER_ORDER if mod in modifiers]
    key = base.lower()

    if ordered:
        return "-".join([*ordered, key])
    return key
