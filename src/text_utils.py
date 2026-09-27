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
