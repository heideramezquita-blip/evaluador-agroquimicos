from __future__ import annotations

import re
import unicodedata

from .cas_utils import CAS_PATTERN, canonicalize_groups, is_valid_cas
from .context_classifier import has_composition_marker
from .models import CompositionComponentEvidence, PdfDocument, PdfTextBlock
from .text_utils import match_key


_CAS_PREFIX = re.compile(r"(?<!\d)(\d{2,7})\s*-\s*(\d{2})\s*-\s*$")
_RANGE_VALUE = re.compile(r"^\s*(\d+(?:[.,]\d+)?(?:\s*-\s*\d+(?:[.,]\d+)?)?)\s*$")

_STOP_KEYS = (
    "seccion 4",
    "section 4",
    "primeros auxilios",
    "first aid",
)

_HEADER_CUES = (
    "nombre quimico",
    "chemical name",
)

_META_CUES = (
    "cas",
    "concentracion",
    "contenido",
    "porcentaje",
    "en peso",
    "w w",
)


def _clean(value: str) -> str:
    value = unicodedata.normalize("NFKC", value or "")
    value = "".join(ch if ch.isprintable() or ch in "\t " else " " for ch in value)
    return re.sub(r"\s+", " ", value).strip()


def _lines(value: str) -> list[str]:
    return [cleaned for raw in (value or "").splitlines() if (cleaned := _clean(raw))]


def _valid_cas(text: str) -> list[str]:
    values: list[str] = []
    for match in CAS_PATTERN.finditer(text or ""):
        cas = canonicalize_groups(*match.groups())
        if is_valid_cas(cas) and cas not in values:
            values.append(cas)
    return values


def _name_like(value: str) -> bool:
    value = _clean(value)
    key = match_key(value)
    if not value or not key or len(value) > 120:
        return False
    if not re.search(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]", value):
        return False
    if ":" in value:
        return False
    if len(key.split()) > 10:
        return False
    if any(
        key.startswith(prefix)
        for prefix in (
            "nombre quimico",
            "chemical name",
            "seccion",
            "section",
            "factor m",
            "classification",
            "international ghs",
            "clasificacion",
        )
    ):
        return False
    return True


def _is_composition_header(block: PdfTextBlock) -> bool:
    key = match_key(block.text)
    return (
        any(cue in key for cue in _HEADER_CUES)
        and "cas" in key
        and any(cue in key for cue in _META_CUES[1:])
    )


def _row_cas(block: PdfTextBlock, nearby: list[PdfTextBlock]) -> str:
    direct = _valid_cas(block.text)
    if len(direct) == 1:
        return direct[0]

    block_lines = _lines(block.text)
    for line in block_lines:
        match = _CAS_PREFIX.search(line)
        if not match:
            continue

        for candidate in nearby:
            candidate_lines = _lines(candidate.text)
            if len(candidate_lines) != 1 or not re.fullmatch(r"\d", candidate_lines[0]):
                continue
            if candidate.y0 < block.y0 - 3 or candidate.y0 > block.y1 + 25:
                continue
            if candidate.x0 < block.x0 - 10 or candidate.x0 > block.x1 + 20:
                continue

            cas = f"{match.group(1)}-{match.group(2)}-{candidate_lines[0]}"
            if is_valid_cas(cas):
                return cas

    return ""


def _row_concentration(block: PdfTextBlock, nearby: list[PdfTextBlock]) -> str:
    lines = _lines(block.text)

    cas_seen = False
    for line in lines[1:]:
        if _valid_cas(line) or _CAS_PREFIX.search(line):
            cas_seen = True
            continue
        if cas_seen:
            match = _RANGE_VALUE.fullmatch(line)
            if match:
                return match.group(1)

    candidates: list[tuple[float, str]] = []
    for candidate in nearby:
        if abs(candidate.y0 - block.y0) > 28:
            continue
        for line in _lines(candidate.text)[:2]:
            match = _RANGE_VALUE.fullmatch(line)
            if match:
                candidates.append((abs(candidate.y0 - block.y0), match.group(1)))

    return min(candidates, default=(0.0, ""), key=lambda item: item[0])[1]


def _row_context(header: PdfTextBlock, block: PdfTextBlock, nearby: list[PdfTextBlock]) -> str:
    pieces = [header.text, block.text]
    for candidate in nearby:
        if candidate is block:
            continue
        if abs(candidate.y0 - block.y0) <= 30:
            pieces.append(candidate.text)
    return " | ".join(_clean(piece) for piece in pieces if _clean(piece))


def extract_composition_components(document: PdfDocument) -> list[CompositionComponentEvidence]:
    """Extract named Section 3 mixture components without promoting them to active ingredients.

    This layer is intentionally descriptive. An SDS mixture table can contain
    active ingredients, solvents, salts, neutralizers or other formulation
    components. The extractor therefore exposes the documentary identity,
    CAS and concentration but leaves the active-ingredient role unconfirmed
    unless another document explicitly establishes it.
    """
    evidence: list[CompositionComponentEvidence] = []

    for page in document.pages:
        if not page.blocks or not has_composition_marker(page.text or ""):
            continue

        headers = [
            (index, block)
            for index, block in enumerate(page.blocks)
            if _is_composition_header(block)
        ]
        for header_index, header in headers:
            following = page.blocks[header_index + 1 :]
            stop_y = None
            for candidate in following:
                key = match_key(candidate.text)
                if any(key.startswith(prefix) for prefix in _STOP_KEYS):
                    stop_y = candidate.y0
                    break

            row_blocks = [
                block
                for block in following
                if block.y0 >= header.y1 - 2
                and (stop_y is None or block.y0 < stop_y)
            ]

            for block in row_blocks:
                lines = _lines(block.text)
                if not lines:
                    continue

                name = lines[0].strip(" :-/|;,.")
                if not _name_like(name):
                    continue

                # Require chemical-row evidence. This prevents hazard/classification
                # prose from becoming a composition component.
                cas = _row_cas(block, row_blocks)
                concentration = _row_concentration(block, row_blocks)
                has_partial_cas = any(_CAS_PREFIX.search(line) for line in lines)
                if not cas and not has_partial_cas:
                    continue
                if not cas and not concentration:
                    continue

                evidence.append(
                    CompositionComponentEvidence(
                        name=name,
                        source_file=document.file_name,
                        page=page.page,
                        concentration=concentration,
                        cas=cas,
                        context=_row_context(header, block, row_blocks),
                    )
                )

            if evidence:
                break

    unique: list[CompositionComponentEvidence] = []
    seen: set[tuple[str, str, str]] = set()
    for item in evidence:
        key = (item.source_file, match_key(item.name), item.cas)
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique
