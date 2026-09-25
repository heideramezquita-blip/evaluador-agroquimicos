from __future__ import annotations

import re
import unicodedata


def strip_accents(value: str) -> str:
    value = unicodedata.normalize("NFD", value)
    return "".join(ch for ch in value if unicodedata.category(ch) != "Mn")


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    value = value.replace("\u00a0", " ").replace("\ufeff", " ")
    value = strip_accents(value.lower())
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def compact_context(lines: list[str], max_chars: int = 600) -> str:
    text = " | ".join(line.strip() for line in lines if line.strip())
    text = re.sub(r"\s+", " ", text)
    if len(text) > max_chars:
        return text[: max_chars - 1] + "…"
    return text


def _name_key(value: str) -> tuple[str, ...]:
    value = normalize_text(value)
    value = re.sub(r"\[[^\]]*\]", " ", value)
    value = re.sub(r"\([^)]*\)", " ", value)
    tokens = re.findall(r"[a-z0-9]+", value)
    return tuple(sorted(tokens))


def chemical_name_variants(value: str | None) -> list[str]:
    if not value:
        return []
    variants = [piece.strip(" *.;") for piece in str(value).split(";")]
    return [v for v in variants if v]


def names_equivalent(left: str | None, right: str | None) -> bool:
    if not left or not right:
        return False
    right_key = _name_key(right)
    if not right_key:
        return False
    return any(_name_key(variant) == right_key for variant in chemical_name_variants(left))


def name_appears_in_text(name: str | None, text: str | None) -> bool:
    if not name or not text:
        return False
    normalized_name = normalize_text(name)
    normalized_text = normalize_text(text)
    if not normalized_name or not normalized_text:
        return False
    pattern = rf"(?<![a-z0-9-]){re.escape(normalized_name)}(?![a-z0-9-])"
    return re.search(pattern, normalized_text) is not None


_CAS_INLINE = re.compile(r"(?<!\d)\d{2,7}-\d{2}-\d(?!\d)")


def active_name_local_to_cas(name: str | None, cas: str, context: str | None, max_segments: int = 5) -> bool:
    if not name or not cas or not context:
        return False
    segments = [segment.strip() for segment in context.split(" | ") if segment.strip()]
    cas_indexes = [i for i, segment in enumerate(segments) if cas in segment]
    if not cas_indexes:
        return False
    name_indexes = [i for i, segment in enumerate(segments) if name_appears_in_text(name, segment)]
    if not name_indexes:
        return False

    for ci in cas_indexes:
        for ni in name_indexes:
            if abs(ci - ni) > max_segments:
                continue
            lo, hi = sorted((ci, ni))
            between = segments[lo + 1 : hi]
            other_cas_between = any(
                found != cas
                for segment in between
                for found in _CAS_INLINE.findall(normalize_text(segment))
            )
            if not other_cas_between:
                return True
    return False
