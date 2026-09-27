from __future__ import annotations

import re
import unicodedata

from .cas_utils import CAS_PATTERN, canonicalize_groups, is_valid_cas
from .models import ActiveIngredientEvidence, PdfDocument, PdfTextBlock
from .text_utils import match_key, normalize_text


_ACTIVE_LABEL_PATTERNS = (
    re.compile(
        r"(?i)^\s*ingrediente\s*(?:\(s\)|s|\s+s)?\s+"
        r"activo\s*(?:\(s\)|s|\s+s)?\s*:?\s*(.*)$"
    ),
    re.compile(
        r"(?i)^\s*principio\s*(?:\(s\)|s|\s+s)?\s+"
        r"activo\s*(?:\(s\)|s|\s+s)?\s*:?\s*(.*)$"
    ),
    re.compile(
        r"(?i)^\s*active\s+ingredient\s*(?:\(s\)|s|\s+s)?\s*:?\s*(.*)$"
    ),
    re.compile(r"(?i)^\s*i\s*\.?\s*a\s*\.?\s*:?\s*(.*)$"),
)

_CONCENTRATION = re.compile(
    r"(?i)(\d+(?:[.,]\d+)?\s*"
    r"(?:%|g\s*/\s*(?:litros?|kg|l)|mg\s*/\s*(?:litros?|kg|l)|"
    r"kg\s*/\s*(?:l|ha)|g\s+l-?1|g\s+kg-?1))"
)

_STOP_PREFIXES = (
    "ingrediente aditivo",
    "ingredientes aditivos",
    "aditivo",
    "aditivos",
    "otros ingredientes",
    "otras sustancias",
    "categoria toxicologica",
    "categoria",
    "presentacion",
    "grupo quimico",
    "modo de accion",
    "mecanismo de accion",
    "generalidades",
    "beneficios",
    "cultivos",
    "blancos biologicos",
    "recomendaciones de uso",
    "instrucciones de uso",
    "instrucciones de uso y manejo",
    "precauciones",
    "medidas de primeros auxilios",
    "propiedades fisicas",
    "propiedades fisicoquimicas",
    "informacion toxicologica",
    "informacion ecologica",
    "registro nacional",
    "titular del registro",
    "uso agricola",
)

_FIELD_PREFIXES = (
    "cas",
    "numero cas",
    "n cas",
    "concentracion",
    "contenido",
    "pureza",
    "nombre quimico",
    "nombre iupac",
    "grupo quimico",
    "formulacion",
    "tipo de formulacion",
    "formula molecular",
    "peso molecular",
    "clasificacion",
)

_NAME_VALUE_PREFIXES = (
    "nombre comun",
    "common name",
    "nombre del ingrediente",
)


def _clean_visible_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value or "")
    value = "".join(
        char if char.isprintable() or char in "\t " else " "
        for char in value
    )
    return re.sub(r"\s+", " ", value).strip()


def _semantic_lines(text: str) -> list[str]:
    return [
        cleaned
        for raw in (text or "").splitlines()
        if (cleaned := _clean_visible_text(raw))
    ]


def _active_label_tail(line: str) -> str | None:
    """Return label tail only for an explicit field-style active label.

    Narrative sentences such as "a base de los ingredientes activos X e Y"
    are deliberately ignored. They may corroborate identity, but must not
    open an extraction window that absorbs surrounding prose.
    """
    cleaned = _clean_visible_text(line)
    for pattern in _ACTIVE_LABEL_PATTERNS:
        match = pattern.match(cleaned)
        if match:
            return match.group(1).strip(" :-/|")
    return None


def _is_stop(line: str) -> bool:
    key = match_key(line)
    if any(key.startswith(prefix) for prefix in _STOP_PREFIXES):
        return True
    if re.fullmatch(r"(?:seccion\s*)?\d{1,2}\s+[a-z].*", key):
        return True
    return False


def _field_value_candidate(line: str) -> str:
    key = match_key(line)
    for prefix in _NAME_VALUE_PREFIXES:
        if key.startswith(prefix):
            parts = re.split(r"\s*:\s*", line, maxsplit=1)
            return parts[1].strip() if len(parts) == 2 else ""
    return ""


def _is_field_line(line: str) -> bool:
    key = match_key(line)
    return any(key.startswith(prefix) for prefix in _FIELD_PREFIXES)


def _starts_structural_field(lines: list[str]) -> bool:
    """Detect field labels split by PDF extraction across adjacent lines.

    Example observed in NINKHA:
        "Nombre"
        "químico:"
        "3-iodo-..."

    Without recombining the first semantic lines, "Nombre" and "químico"
    can be misread as separate active ingredients.
    """
    if not lines:
        return False

    prefixes = _FIELD_PREFIXES + _STOP_PREFIXES + _NAME_VALUE_PREFIXES
    for size in range(1, min(3, len(lines)) + 1):
        combined = match_key(" ".join(lines[:size]))
        if any(
            combined == prefix or combined.startswith(prefix + " ")
            for prefix in prefixes
        ):
            return True
    return False


def _extract_concentration(line: str) -> str:
    match = _CONCENTRATION.search(line or "")
    return match.group(1).strip() if match else ""


def _strip_concentration(line: str) -> str:
    value = _CONCENTRATION.sub(" ", line or "")
    value = CAS_PATTERN.sub(" ", value)
    value = re.sub(r"(?i)\b(?:n[uú]mero\s+)?cas\b\s*[:#-]?", " ", value)
    value = re.sub(r"(?i)\(\s*formulaci[oó]n[^)]*\)", " ", value)
    value = re.sub(r"\(\s*\)", " ", value)
    value = re.sub(r"\s*\+\s*$", " ", value)
    value = re.sub(r"\s*[/|;,]+\s*$", " ", value)
    return re.sub(r"\s+", " ", value).strip(" :-/|;,.+()")


def _looks_like_name(line: str) -> bool:
    value = _strip_concentration(_clean_visible_text(line))
    key = match_key(value)
    if not key or len(key) < 3:
        return False
    if _is_stop(value) or _is_field_line(value):
        return False
    if _active_label_tail(value) is not None:
        return False
    if ":" in value:
        return False
    if not re.search(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]", value):
        return False
    words = key.split()
    if len(words) > 12 or len(value) > 120:
        return False
    prose_markers = (
        "debe ser",
        "se recomienda",
        "para el control",
        "modo de accion",
        "uso agricola",
        "producto formulado",
        "contiene los siguientes",
        "actua sobre",
        "afecta el",
        "es un insecticida",
        "es un herbicida",
        "es un fungicida",
        "es un piretroide",
        "posee prolongado",
        "sistema nervioso",
        "plagas objetivo",
        "escuchamos aprendemos solucionamos",
    )
    normalized = normalize_text(value)
    if any(marker in normalized for marker in prose_markers):
        return False
    return True


def _valid_cas_in_text(text: str) -> list[str]:
    values: list[str] = []
    for match in CAS_PATTERN.finditer(text or ""):
        cas = canonicalize_groups(*match.groups())
        if is_valid_cas(cas) and cas not in values:
            values.append(cas)
    return values


def _split_candidate_line(line: str) -> list[str]:
    """Split multi-active rows without splitting concentration syntax."""
    cleaned = _clean_visible_text(line)
    parts = [
        part.strip()
        for part in re.split(r"\s+\+\s+|\s+\+\s*$", cleaned)
        if part.strip()
    ]
    return parts or ([cleaned] if cleaned else [])


def _candidate_tuples(lines: list[str]) -> list[tuple[str, str, str]]:
    candidates: list[tuple[str, str, str]] = []

    for line in lines:
        if _is_stop(line):
            break

        field_value = _field_value_candidate(line)
        candidate_line = field_value or line
        if not field_value and _is_field_line(candidate_line):
            continue

        for part in _split_candidate_line(candidate_line):
            if not _looks_like_name(part):
                continue

            name = _strip_concentration(part)
            concentration = _extract_concentration(part)
            same_line_cas = _valid_cas_in_text(part)
            candidates.append(
                (
                    _clean_visible_text(name),
                    concentration,
                    same_line_cas[0] if len(same_line_cas) == 1 else "",
                )
            )

    if len(candidates) == 1:
        name, concentration, cas = candidates[0]
        block_text = " | ".join(lines)
        if not concentration:
            concentration = _extract_concentration(block_text)
        if not cas:
            block_cas = _valid_cas_in_text(block_text)
            cas = block_cas[0] if len(block_cas) == 1 else ""
        candidates[0] = (name, concentration, cas)

    return candidates


def _horizontal_overlap(a: PdfTextBlock, b: PdfTextBlock) -> float:
    overlap = max(0.0, min(a.x1, b.x1) - max(a.x0, b.x0))
    width = max(1.0, min(a.x1 - a.x0, b.x1 - b.x0))
    return overlap / width


def _same_column(label: PdfTextBlock, candidate: PdfTextBlock) -> bool:
    return (
        _horizontal_overlap(label, candidate) >= 0.45
        or abs(label.x0 - candidate.x0) <= 36
    )


def _block_window(blocks: list[PdfTextBlock], label_index: int) -> tuple[list[str], str]:
    label = blocks[label_index]
    label_lines = _semantic_lines(label.text)
    payload: list[str] = []

    # Keep anything following the explicit label inside the same PDF block.
    for index, line in enumerate(label_lines):
        tail = _active_label_tail(line)
        if tail is None:
            continue
        if tail:
            payload.append(tail)
        payload.extend(label_lines[index + 1 :])
        break

    # Then inspect only geometrically aligned blocks immediately below the
    # label. This prevents a two-column FT from mixing the active-ingredient
    # sidebar with "Modo de Acción" or other prose from the main column.
    aligned_texts = [label.text]
    max_bottom = label.y1 + 150
    for candidate in blocks[label_index + 1 :]:
        if candidate.y0 > max_bottom:
            break
        if candidate.y0 + 2 < label.y0:
            continue
        if not _same_column(label, candidate):
            continue

        lines = _semantic_lines(candidate.text)
        if not lines:
            continue

        if _is_stop(lines[0]) or _starts_structural_field(lines):
            aligned_texts.append(candidate.text)
            break

        # Another explicit active label starts a separate block, not a
        # continuation of this one.
        if _active_label_tail(lines[0]) is not None:
            break

        aligned_texts.append(candidate.text)
        payload.extend(lines)

        # A concentration-bearing aligned block is normally the identity row.
        # Continue only until the next aligned section heading, which is
        # handled by the stop logic above.
        max_bottom = max(max_bottom, candidate.y1 + 70)

    return payload, " | ".join(_clean_visible_text(x) for x in aligned_texts)


def _evidence_from_candidates(
    candidates: list[tuple[str, str, str]],
    *,
    source_file: str,
    page_number: int,
    context: str,
) -> list[ActiveIngredientEvidence]:
    evidence: list[ActiveIngredientEvidence] = []
    seen: set[str] = set()

    for name, concentration, cas in candidates:
        key = match_key(name)
        if not key or key in seen:
            continue
        seen.add(key)
        evidence.append(
            ActiveIngredientEvidence(
                name=name,
                source_file=source_file,
                page=page_number,
                concentration=concentration,
                cas=cas,
                context=context,
            )
        )
    return evidence


def _extract_from_blocks(
    blocks: list[PdfTextBlock],
    source_file: str,
    page_number: int,
) -> list[ActiveIngredientEvidence]:
    evidence: list[ActiveIngredientEvidence] = []

    for block_index, block in enumerate(blocks):
        lines = _semantic_lines(block.text)
        if not any(_active_label_tail(line) is not None for line in lines):
            continue

        payload, context = _block_window(blocks, block_index)
        evidence.extend(
            _evidence_from_candidates(
                _candidate_tuples(payload),
                source_file=source_file,
                page_number=page_number,
                context=context,
            )
        )

    return evidence


def _extract_from_lines(
    text: str,
    source_file: str,
    page_number: int,
) -> list[ActiveIngredientEvidence]:
    """Fallback for synthetic fixtures or PDFs without block metadata."""
    lines = _semantic_lines(text)
    evidence: list[ActiveIngredientEvidence] = []

    for marker_index, line in enumerate(lines):
        tail = _active_label_tail(line)
        if tail is None:
            continue

        payload: list[str] = []
        if tail:
            payload.append(tail)

        for candidate in lines[marker_index + 1 : marker_index + 8]:
            if _is_stop(candidate) or _active_label_tail(candidate) is not None:
                break
            payload.append(candidate)

        context = " | ".join(
            lines[max(0, marker_index - 2) : min(len(lines), marker_index + 8)]
        )
        evidence.extend(
            _evidence_from_candidates(
                _candidate_tuples(payload),
                source_file=source_file,
                page_number=page_number,
                context=context,
            )
        )

    return evidence


def extract_active_ingredients(document: PdfDocument) -> list[ActiveIngredientEvidence]:
    """Extract explicitly labelled active ingredients independently of list matches."""
    evidence: list[ActiveIngredientEvidence] = []

    for page in document.pages:
        if page.blocks:
            evidence.extend(
                _extract_from_blocks(page.blocks, document.file_name, page.page)
            )
        else:
            evidence.extend(
                _extract_from_lines(page.text or "", document.file_name, page.page)
            )

    # Deduplicate repeated product headers/blocks while preserving the strongest
    # concentration/CAS and the first page where identity was explicitly shown.
    by_key: dict[tuple[str, str], ActiveIngredientEvidence] = {}
    for item in evidence:
        key = (item.source_file, match_key(item.name))
        current = by_key.get(key)
        if current is None:
            by_key[key] = item
            continue
        if not current.concentration and item.concentration:
            current.concentration = item.concentration
        if not current.cas and item.cas:
            current.cas = item.cas

    return list(by_key.values())
