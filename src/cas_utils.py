from __future__ import annotations

import re

DASHES = "-‐‑‒–—−\u00ad"
_DASH_CLASS = re.escape(DASHES)

# Do not match the CAS-shaped suffix of longer hyphenated identifiers such as
# EU INDEX numbers (for example 613-088-00-6). Those suffixes can even pass a
# CAS checksum and would otherwise become false chemical identities.
CAS_PATTERN = re.compile(
    rf"(?<![\d{_DASH_CLASS}])(\d{{2,7}})\s*[{_DASH_CLASS}]\s*"
    rf"(\d{{2}})\s*[{_DASH_CLASS}]\s*(\d)(?![\d{_DASH_CLASS}])"
)
DIGITS_ONLY_PATTERN = re.compile(r"(?<!\d)(\d{5,10})(?!\d)")


def canonicalize_groups(a, b, c):
    return f"{a}-{b}-{c}"


def normalize_cas(value, *, allow_digits_only=False):
    if not value:
        return None
    m = CAS_PATTERN.search(str(value))
    if m:
        return canonicalize_groups(*m.groups())
    if allow_digits_only:
        token = re.sub(r"\D", "", str(value))
        if 5 <= len(token) <= 10:
            return f"{token[:-3]}-{token[-3:-1]}-{token[-1]}"
    return None


def is_valid_cas(value):
    cas = normalize_cas(value, allow_digits_only=True)
    if not cas:
        return False
    a, b, c = cas.split("-")
    digits = a + b
    return (
        sum(int(digit) * weight for weight, digit in enumerate(reversed(digits), 1))
        % 10
        == int(c)
    )


def extract_cas_candidates(text):
    out = []
    for m in CAS_PATTERN.finditer(text or ""):
        cas = canonicalize_groups(*m.groups())
        if cas not in out:
            out.append(cas)
    return out


def extract_valid_cas(text):
    return [value for value in extract_cas_candidates(text) if is_valid_cas(value)]


def parse_manual_cas(text):
    valid = []
    invalid = []
    spans = []

    for m in CAS_PATTERN.finditer(text or ""):
        cas = canonicalize_groups(*m.groups())
        spans.append(m.span())
        target = valid if is_valid_cas(cas) else invalid
        if cas not in target:
            target.append(cas)

    for m in DIGITS_ONLY_PATTERN.finditer(text or ""):
        if any(m.start() >= start and m.end() <= end for start, end in spans):
            continue
        token = m.group()
        cas = f"{token[:-3]}-{token[-3:-1]}-{token[-1]}"
        target = valid if is_valid_cas(cas) else invalid
        if cas not in target:
            target.append(cas)

    return valid, invalid
