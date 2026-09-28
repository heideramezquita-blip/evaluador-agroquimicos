from __future__ import annotations

import re

from .cas_utils import (
    SPLIT_CAS_PREFIX_PATTERN,
    extract_valid_cas,
    reconstruct_split_cas,
)
from .context_classifier import has_composition_marker
from .models import CompositionComponentEvidence, PdfDocument, PdfTextBlock
from .text_utils import clean_visible_text, match_key, semantic_lines


_RANGE_VALUE = re.compile(
    r"^\s*((?:[<>]=?\s*)?\d+(?:[.,]\d+)?"
    r"(?:\s*-\s*(?:[<>]=?\s*)?\d+(?:[.,]\d+)?)?)\s*$"
)

_STOP_KEYS = (
    "seccion 4",
    "section 4",
    "primeros auxilios",
    "first aid",
)

_HEADER_CUES = (
    "nombre quimico",
    "chemical name",
    "componente",
    "component",
)

_META_CUES = (
    "cas",
    "concentracion",
    "contenido",
    "porcentaje",
    "en peso",
    "w w",
)


def _name_like(value: str) -> bool:
    value = clean_visible_text(value)
    key = match_key(value)
    # Section 3 can legitimately contain long systematic component names.
    # A valid CAS is required later before a row is accepted, so this can be
    # more permissive than active-ingredient free-text heuristics.
    if not value or not key or len(value) > 220:
        return False
    if not re.search(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]", value):
        return False
    if ":" in value:
        # Stoichiometric ratios are part of legitimate chemical names, e.g.
        # reaction masses ending in "(3:1)". Other colon-bearing prose remains
        # structural/non-name text.
        without_ratio = re.sub(r"\(\s*\d+\s*:\s*\d+\s*\)", "", value)
        if ":" in without_ratio:
            return False
    if len(key.split()) > 32:
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


def _is_composition_header_text(text: str) -> bool:
    key = match_key(text)
    has_name_column = (
        "nombre quimico" in key
        or "chemical name" in key
        or re.search(r"\bcomponentes?\b", key) is not None
    )
    return (
        has_name_column
        and "cas" in key
        and any(cue in key for cue in _META_CUES[1:])
    )


def _composition_header_span(
    blocks: list[PdfTextBlock],
    index: int,
) -> tuple[int, PdfTextBlock] | None:
    """Recognize a composition header even when PDF columns are split.

    Some SDS files extract the left header ("Nombre químico / No. CAS") and
    right header ("Clasificación / Concentración") as separate overlapping
    text blocks. The table is still structurally clear, so merge only nearby
    header blocks until the required cues are present.
    """
    block = blocks[index]
    if not any(cue in match_key(block.text) for cue in _HEADER_CUES):
        return None

    pieces = [block]
    if _is_composition_header_text(block.text):
        return index + 1, block

    for cursor in range(index + 1, min(len(blocks), index + 5)):
        candidate = blocks[cursor]
        if candidate.y0 > block.y1 + 3:
            break
        pieces.append(candidate)
        combined = "\n".join(piece.text for piece in pieces)
        if not _is_composition_header_text(combined):
            continue
        return cursor + 1, PdfTextBlock(
            min(piece.x0 for piece in pieces),
            min(piece.y0 for piece in pieces),
            max(piece.x1 for piece in pieces),
            max(piece.y1 for piece in pieces),
            combined,
        )

    return None


def _row_cas(block: PdfTextBlock, nearby: list[PdfTextBlock]) -> str:
    direct = extract_valid_cas(block.text)
    if len(direct) == 1:
        return direct[0]

    # In multi-column SDS tables the chemical name and identifier column can
    # be separate blocks on the same row. Accept a single valid CAS from the
    # horizontally adjacent identifier block. EU Index numbers such as
    # 613-167-00-5 are already excluded by CAS_PATTERN in cas_utils.
    adjacent: list[tuple[float, str]] = []
    for candidate in nearby:
        if candidate is block:
            continue
        if abs(candidate.y0 - block.y0) > 8:
            continue
        if candidate.x0 < block.x1 - 5:
            continue
        values = extract_valid_cas(candidate.text)
        if len(values) == 1:
            adjacent.append((candidate.x0 - block.x1, values[0]))
    if adjacent:
        return min(adjacent, key=lambda item: item[0])[1]

    block_lines = semantic_lines(block.text)
    for line in block_lines:
        match = SPLIT_CAS_PREFIX_PATTERN.search(line)
        if not match:
            continue

        for candidate in nearby:
            candidate_lines = semantic_lines(candidate.text)
            if len(candidate_lines) != 1 or not re.fullmatch(r"\d", candidate_lines[0]):
                continue
            if candidate.y0 < block.y0 - 3 or candidate.y0 > block.y1 + 25:
                continue
            if candidate.x0 < block.x0 - 10 or candidate.x0 > block.x1 + 20:
                continue

            cas = reconstruct_split_cas(line, candidate_lines[0])
            if cas:
                return cas

    return ""


def _row_concentration(block: PdfTextBlock, nearby: list[PdfTextBlock]) -> str:
    lines = semantic_lines(block.text)

    # Some table cells wrap a comparator range across two PDF blocks, e.g.
    # ">= 0,0002 - <" + "0,0015". Rejoin only vertically adjacent pieces
    # from the same concentration column.
    partial_range = re.compile(
        r"^\s*((?:[<>]=?\s*)?\d+(?:[.,]\d+)?\s*-\s*[<>]=?)\s*$"
    )
    numeric_tail = re.compile(r"^\s*(\d+(?:[.,]\d+)?)\s*$")
    for candidate in nearby:
        if abs(candidate.y0 - block.y0) > 8:
            continue
        candidate_lines = semantic_lines(candidate.text)
        if len(candidate_lines) != 1:
            continue
        partial = partial_range.fullmatch(candidate_lines[0])
        if not partial:
            continue
        for tail in nearby:
            if tail is candidate:
                continue
            tail_lines = semantic_lines(tail.text)
            if len(tail_lines) != 1:
                continue
            number = numeric_tail.fullmatch(tail_lines[0])
            if not number:
                continue
            if tail.y0 < candidate.y0 or tail.y0 > candidate.y1 + 20:
                continue
            if abs(tail.x0 - candidate.x0) > 30:
                continue
            return f"{partial.group(1)} {number.group(1)}"

    cas_seen = False
    for line in lines[1:]:
        if extract_valid_cas(line) or SPLIT_CAS_PREFIX_PATTERN.search(line):
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
        candidate_lines = semantic_lines(candidate.text)
        if (
            len(candidate_lines) == 1
            and any(
                reconstruct_split_cas(line, candidate_lines[0])
                for line in lines
                if SPLIT_CAS_PREFIX_PATTERN.search(line)
            )
        ):
            # This one-digit cell is the CAS checksum, not a percentage.
            continue
        for line in candidate_lines[:2]:
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
    cleaned = [clean_visible_text(piece) for piece in pieces]
    return " | ".join(piece for piece in cleaned if piece)


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

        headers = []
        for index in range(len(page.blocks)):
            span = _composition_header_span(page.blocks, index)
            if span is None:
                continue
            header_end_index, header = span
            headers.append((index, header_end_index, header))

        for header_index, header_end_index, header in headers:
            following = page.blocks[header_end_index:]
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
                lines = semantic_lines(block.text)
                if not lines:
                    continue

                # Require chemical-row evidence before deciding how much of a
                # multi-line cell belongs to the chemical name.
                cas = _row_cas(block, row_blocks)
                direct_cas = extract_valid_cas(block.text)
                has_partial_cas = any(
                    SPLIT_CAS_PREFIX_PATTERN.search(line)
                    for line in lines
                )
                if cas and not direct_cas and not has_partial_cas:
                    # Name and identifier occupy separate table columns:
                    # preserve the full wrapped systematic chemical name.
                    name = " ".join(lines).strip(" :-/|;,.")
                    name = re.sub(r"-\s+(?=[A-Za-z0-9])", "-", name)
                else:
                    name = lines[0].strip(" :-/|;,.")
                if not _name_like(name):
                    continue

                # This prevents hazard/classification prose from becoming a
                # composition component.
                concentration = _row_concentration(block, row_blocks)
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
