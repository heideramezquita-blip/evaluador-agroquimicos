from __future__ import annotations

from collections import OrderedDict

from .cas_utils import CAS_PATTERN, canonicalize_groups, is_valid_cas
from .models import CasOccurrence, CasRecord, PdfDocument
from .text_utils import compact_context, normalize_text


ACTIVE_MARKERS = (
    "ingrediente activo",
    "ingredientes activos",
    "active ingredient",
    "active ingredients",
    "cas ingrediente activo",
    "cas del ingrediente activo",
    "no cas ingrediente activo",
    "numero cas ingrediente activo",
    "identidad ingrediente activo",
)


def _context_role(lines: list[str]) -> str:
    normalized = normalize_text(" ".join(lines))
    if any(phrase in normalized for phrase in (
        "ingredientes activos no aplica",
        "ingrediente activo no aplica",
        "active ingredients not applicable",
        "active ingredient not applicable",
        "active ingredients n/a",
    )):
        active_marker = False
    else:
        active_marker = any(marker in normalized for marker in ACTIVE_MARKERS)
    if active_marker:
        return "active_explicit"
    if any(marker in normalized for marker in (
        "composicion/informacion sobre los componentes",
        "composicion/informacion sobre los ingredientes",
        "composicion / informacion sobre los componentes",
        "composicion / informacion sobre los ingredientes",
        "nombre quimico cas",
        "componentes cas",
    )):
        return "component"
    return "unknown"


def extract_document_cas(document: PdfDocument) -> tuple[list[CasRecord], list[dict]]:
    by_cas: OrderedDict[str, CasRecord] = OrderedDict()
    invalid: list[dict] = []

    for page in document.pages:
        text = page.text or ""
        if not text:
            continue
        lines = text.splitlines()

        for match in CAS_PATTERN.finditer(text):
            cas = canonicalize_groups(match.group(1), match.group(2), match.group(3))
            line_index = text[: match.start()].count("\n")
            start = max(0, line_index - 4)
            end = min(len(lines), line_index + 5)
            context_lines = lines[start:end]
            context = compact_context(context_lines)

            if not is_valid_cas(cas):
                invalid.append({
                    "candidate": cas,
                    "source_file": document.file_name,
                    "page": page.page,
                    "context": context,
                })
                continue

            occurrence = CasOccurrence(
                cas=cas,
                source_file=document.file_name,
                page=page.page,
                source="document",
                role=_context_role(context_lines),
                context=context,
            )
            if cas not in by_cas:
                by_cas[cas] = CasRecord(cas=cas)
            if not any(
                o.source_file == occurrence.source_file
                and o.page == occurrence.page
                and o.context == occurrence.context
                for o in by_cas[cas].occurrences
            ):
                by_cas[cas].occurrences.append(occurrence)

    return list(by_cas.values()), invalid


def merge_cas_records(record_groups: list[list[CasRecord]]) -> list[CasRecord]:
    by_cas: OrderedDict[str, CasRecord] = OrderedDict()
    for records in record_groups:
        for record in records:
            if record.cas not in by_cas:
                by_cas[record.cas] = CasRecord(cas=record.cas)
            existing = by_cas[record.cas]
            for occurrence in record.occurrences:
                if not any(
                    o.source_file == occurrence.source_file
                    and o.page == occurrence.page
                    and o.source == occurrence.source
                    and o.context == occurrence.context
                    and o.role == occurrence.role
                    for o in existing.occurrences
                ):
                    existing.occurrences.append(occurrence)
    return list(by_cas.values())
