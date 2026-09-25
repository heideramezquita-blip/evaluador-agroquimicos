from __future__ import annotations

import re


DASHES = "-‐‑‒–—−"
CAS_PATTERN = re.compile(
    rf"(?<!\d)(\d{{2,7}})\s*[{re.escape(DASHES)}]\s*(\d{{2}})\s*[{re.escape(DASHES)}]\s*(\d)(?!\d)"
)
DIGITS_ONLY_PATTERN = re.compile(r"(?<!\d)(\d{5,10})(?!\d)")


def canonicalize_groups(first: str, second: str, check: str) -> str:
    return f"{first}-{second}-{check}"


def normalize_cas(value: str | None, *, allow_digits_only: bool = False) -> str | None:
    if not value:
        return None
    match = CAS_PATTERN.search(str(value))
    if match:
        return canonicalize_groups(match.group(1), match.group(2), match.group(3))
    if allow_digits_only:
        token = re.sub(r"\D", "", str(value))
        if 5 <= len(token) <= 10:
            return f"{token[:-3]}-{token[-3:-1]}-{token[-1]}"
    return None


def is_valid_cas(value: str | None) -> bool:
    cas = normalize_cas(value, allow_digits_only=True)
    if not cas:
        return False
    first, second, check = cas.split("-")
    digits = first + second
    total = sum(int(digit) * weight for weight, digit in enumerate(reversed(digits), start=1))
    return total % 10 == int(check)


def extract_cas_candidates(text: str) -> list[str]:
    found: list[str] = []
    for match in CAS_PATTERN.finditer(text or ""):
        cas = canonicalize_groups(match.group(1), match.group(2), match.group(3))
        if cas not in found:
            found.append(cas)
    return found


def extract_valid_cas(text: str) -> list[str]:
    return [cas for cas in extract_cas_candidates(text) if is_valid_cas(cas)]


def parse_manual_cas(text: str) -> tuple[list[str], list[str]]:
    """Return (valid, invalid) CAS values from a free-form manual input."""
    valid: list[str] = []
    invalid: list[str] = []
    consumed_spans: list[tuple[int, int]] = []

    for match in CAS_PATTERN.finditer(text or ""):
        cas = canonicalize_groups(match.group(1), match.group(2), match.group(3))
        consumed_spans.append(match.span())
        target = valid if is_valid_cas(cas) else invalid
        if cas not in target:
            target.append(cas)

    def covered(start: int, end: int) -> bool:
        return any(start >= a and end <= b for a, b in consumed_spans)

    for match in DIGITS_ONLY_PATTERN.finditer(text or ""):
        if covered(*match.span()):
            continue
        token = match.group(1)
        cas = f"{token[:-3]}-{token[-3:-1]}-{token[-1]}"
        target = valid if is_valid_cas(cas) else invalid
        if cas not in target:
            target.append(cas)

    return valid, invalid
