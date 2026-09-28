from __future__ import annotations

import re
import unicodedata


_DASH_TRANSLATION = str.maketrans(
    {
        "‐": "-",
        "‑": "-",
        "‒": "-",
        "–": "-",
        "—": "-",
        "−": "-",
        "\u00a0": " ",
    }
)


def clean_visible_text(value: str) -> str:
    """Normalize display/extraction text without folding accents or punctuation."""
    normalized = unicodedata.normalize("NFKC", value or "")
    printable = "".join(
        char if char.isprintable() or char in "\t " else " "
        for char in normalized
    )
    return re.sub(r"\s+", " ", printable).strip()


def semantic_lines(text: str) -> list[str]:
    """Return non-empty, display-normalized lines from extracted document text."""
    return [
        cleaned
        for raw in (text or "").splitlines()
        if (cleaned := clean_visible_text(raw))
    ]


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(char for char in value if not unicodedata.combining(char)).lower()
    value = value.translate(_DASH_TRANSLATION)
    value = re.sub(r"[^a-z0-9%+./-]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def match_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", normalize_text(value)).strip()


def phrase_present(text: str, phrase: str) -> bool:
    text_key = match_key(text)
    phrase_key = match_key(phrase)
    return bool(phrase_key) and f" {phrase_key} " in f" {text_key} "
