from __future__ import annotations

from .cas_utils import CAS_PATTERN, canonicalize_groups, is_valid_cas
from .models import CasOccurrence, CasRecord, PdfDocument
from .text_utils import normalize_text


def _recompact(value: str) -> str:
    return " | ".join(line.strip() for line in value.splitlines() if line.strip())


def _local_context(text: str, start: int, end: int, radius: int = 350) -> str:
    return _recompact(text[max(0, start - radius) : min(len(text), end + radius)])


def _role(context: str) -> str:
    normalized = normalize_text(context)
    return (
        "active_explicit"
        if any(
            marker in normalized
            for marker in ("ingrediente activo", "ingredientes activos", "active ingredient")
        )
        else "unknown"
    )


def extract_document_cas(document: PdfDocument):
    by_cas: dict[str, CasRecord] = {}
    invalid = []

    for page in document.pages:
        text = page.text or ""
        for match in CAS_PATTERN.finditer(text):
            cas = canonicalize_groups(*match.groups())
            context = _local_context(text, match.start(), match.end())

            if not is_valid_cas(cas):
                invalid.append(
                    {
                        "candidate": cas,
                        "source_file": document.file_name,
                        "page": page.page,
                        "context": context,
                    }
                )
                continue

            occurrence = CasOccurrence(
                cas,
                document.file_name,
                page.page,
                "document",
                _role(context),
                context,
            )
            by_cas.setdefault(cas, CasRecord(cas)).occurrences.append(occurrence)

    return list(by_cas.values()), invalid


def merge_cas_records(groups):
    """Merge records while preserving first-seen CAS and occurrence order."""
    by_cas: dict[str, CasRecord] = {}
    occurrence_keys: dict[str, set[tuple]] = {}

    for records in groups:
        for record in records:
            target = by_cas.setdefault(record.cas, CasRecord(record.cas))
            seen = occurrence_keys.setdefault(record.cas, set())

            for occurrence in record.occurrences:
                key = (
                    occurrence.source_file,
                    occurrence.page,
                    occurrence.context,
                    occurrence.source,
                )
                if key in seen:
                    continue
                seen.add(key)
                target.occurrences.append(occurrence)

    return list(by_cas.values())
