from __future__ import annotations

from .cas_utils import (
    CAS_PATTERN,
    canonicalize_groups,
    is_valid_cas,
    reconstruct_split_cas,
    SPLIT_CAS_PREFIX_PATTERN,
)
from .context_classifier import has_active_marker
from .models import CasOccurrence, CasRecord, PdfDocument


def _recompact(value: str) -> str:
    return " | ".join(line.strip() for line in value.splitlines() if line.strip())


def _local_context(text: str, start: int, end: int, radius: int = 350) -> str:
    return _recompact(text[max(0, start - radius) : min(len(text), end + radius)])


def _role(context: str) -> str:
    return "active_explicit" if has_active_marker(context) else "unknown"


def _split_block_cas_occurrences(document: PdfDocument, page) -> list[CasOccurrence]:
    """Recover CAS numbers split into separate PDF text blocks.

    A common table-extraction pattern leaves the final CAS checksum digit in a
    tiny neighbouring block (for example 104098-48- plus 8). Recovery is only
    accepted when the reconstructed CAS passes checksum validation.
    """
    occurrences: list[CasOccurrence] = []
    blocks = page.blocks or []

    for block in blocks:
        lines = [line.strip() for line in (block.text or "").splitlines() if line.strip()]
        prefix_line = next(
            (
                line
                for line in reversed(lines)
                if SPLIT_CAS_PREFIX_PATTERN.search(line)
            ),
            "",
        )
        if not prefix_line:
            continue

        for candidate in blocks:
            if candidate is block:
                continue
            candidate_text = " ".join(
                line.strip()
                for line in (candidate.text or "").splitlines()
                if line.strip()
            )
            if len(candidate_text) != 1 or not candidate_text.isdigit():
                continue
            if candidate.y0 < block.y0 - 3 or candidate.y0 > block.y1 + 25:
                continue
            if candidate.x0 < block.x0 - 10 or candidate.x0 > block.x1 + 20:
                continue

            cas = reconstruct_split_cas(prefix_line, candidate_text)
            if not cas:
                continue

            nearby = [
                neighbour.text
                for neighbour in blocks
                if neighbour.y0 >= max(0.0, block.y0 - 120)
                and neighbour.y0 <= block.y1 + 120
            ]
            context = _recompact("\n".join(nearby))
            occurrences.append(
                CasOccurrence(
                    cas,
                    document.file_name,
                    page.page,
                    "document",
                    _role(context),
                    context,
                    "CAS reconstruido a partir de bloques contiguos del PDF.",
                )
            )
            break

    return occurrences


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

        for occurrence in _split_block_cas_occurrences(document, page):
            target = by_cas.setdefault(occurrence.cas, CasRecord(occurrence.cas))
            duplicate = any(
                existing.source_file == occurrence.source_file
                and existing.page == occurrence.page
                and existing.context == occurrence.context
                for existing in target.occurrences
            )
            if not duplicate:
                target.occurrences.append(occurrence)

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
