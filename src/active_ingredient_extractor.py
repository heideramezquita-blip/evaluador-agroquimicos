from __future__ import annotations

import re
import unicodedata

from .cas_utils import CAS_PATTERN, canonicalize_groups, is_valid_cas
from .context_classifier import has_active_marker
from .models import ActiveIngredientEvidence, PdfDocument
from .text_utils import match_key, normalize_text


_ACTIVE_LABEL_PATTERNS = (
    re.compile(
        r"(?i)\bingrediente\s*(?:\(s\)|s|\s+s)?\s+"
        r"activo\s*(?:\(s\)|s|\s+s)?\s*:?\s*(.*)$"
    ),
    re.compile(
        r"(?i)\bprincipio\s*(?:\(s\)|s|\s+s)?\s+"
        r"activo\s*(?:\(s\)|s|\s+s)?\s*:?\s*(.*)$"
    ),
    re.compile(r"(?i)\bactive\s+ingredient\s*(?:\(s\)|s|\s+s)?\s*:?\s*(.*)$"),
)

_IA_LABEL = re.compile(r"(?i)\bi\s*\.?\s*a\s*\.?\s*:?\s*(.*)$")

_CONCENTRATION = re.compile(
    r"(?i)(\d+(?:[.,]\d+)?\s*"
    r"(?:%|g\s*/\s*(?:l|litro|kg)|mg\s*/\s*(?:l|kg)|"
    r"kg\s*/\s*(?:l|ha)|g\s+l-?1|g\s+kg-?1))"
)

_STOP_PREFIXES = (
    "ingrediente aditivo",
    "ingredientes aditivos",
    "aditivo",
    "aditivos",
    "otros ingredientes",
    "otras sustancias",
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


def _active_tail(line: str) -> str:
    cleaned = _clean_visible_text(line)
    for pattern in _ACTIVE_LABEL_PATTERNS:
        match = pattern.search(cleaned)
        if match:
            return match.group(1).strip(" :-/|")
    if has_active_marker(cleaned):
        match = _IA_LABEL.search(cleaned)
        if match:
            return match.group(1).strip(" :-/|")
    return ""


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


def _extract_concentration(line: str) -> str:
    match = _CONCENTRATION.search(line or "")
    return match.group(1).strip() if match else ""


def _strip_concentration(line: str) -> str:
    value = _CONCENTRATION.sub(" ", line or "")
    value = CAS_PATTERN.sub(" ", value)
    value = re.sub(r"(?i)\b(?:n[uú]mero\s+)?cas\b\s*[:#-]?", " ", value)
    value = re.sub(r"(?i)\(\s*formulaci[oó]n[^)]*\)", " ", value)
    value = re.sub(r"\s*[/|;,]+\s*$", " ", value)
    return re.sub(r"\s+", " ", value).strip(" :-/|;,.")


def _looks_like_name(line: str) -> bool:
    value = _strip_concentration(_clean_visible_text(line))
    key = match_key(value)
    if not key or len(key) < 3:
        return False
    if _is_stop(value) or _is_field_line(value) or has_active_marker(value):
        return False
    if not re.search(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]", value):
        return False
    words = key.split()
    if len(words) > 16 or len(value) > 180:
        return False
    # Avoid prose being promoted to a chemical identity.
    prose_markers = (
        "debe ser",
        "se recomienda",
        "para el control",
        "modo de accion",
        "uso agricola",
        "producto formulado",
        "contiene los siguientes",
    )
    if any(marker in normalize_text(value) for marker in prose_markers):
        return False
    return True


def _valid_cas_in_text(text: str) -> list[str]:
    values: list[str] = []
    for match in CAS_PATTERN.finditer(text or ""):
        cas = canonicalize_groups(*match.groups())
        if is_valid_cas(cas) and cas not in values:
            values.append(cas)
    return values


def _extract_block(
    lines: list[str],
    marker_index: int,
    source_file: str,
    page_number: int,
) -> list[ActiveIngredientEvidence]:
    block: list[str] = []
    tail = _active_tail(lines[marker_index])
    if tail:
        block.append(tail)

    for line in lines[marker_index + 1 : marker_index + 11]:
        if _is_stop(line) or (has_active_marker(line) and block):
            break
        block.append(line)

    candidates: list[tuple[str, str, str]] = []
    for line in block:
        field_value = _field_value_candidate(line)
        candidate_line = field_value or line
        if not field_value and _is_field_line(candidate_line):
            continue
        if not _looks_like_name(candidate_line):
            continue

        name = _strip_concentration(candidate_line)
        concentration = _extract_concentration(candidate_line)
        same_line_cas = _valid_cas_in_text(candidate_line)
        candidates.append(
            (
                _clean_visible_text(name),
                concentration,
                same_line_cas[0] if len(same_line_cas) == 1 else "",
            )
        )

    # A single ingredient often has its concentration/CAS on adjacent rows.
    # Associate those fields only when the block has one candidate, avoiding
    # false pairings in multi-active tables.
    if len(candidates) == 1:
        name, concentration, cas = candidates[0]
        block_text = " | ".join(block)
        if not concentration:
            concentration = _extract_concentration(block_text)
        if not cas:
            block_cas = _valid_cas_in_text(block_text)
            cas = block_cas[0] if len(block_cas) == 1 else ""
        candidates[0] = (name, concentration, cas)

    context = " | ".join(
        lines[max(0, marker_index - 2) : min(len(lines), marker_index + 11)]
    )

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


def extract_active_ingredients(document: PdfDocument) -> list[ActiveIngredientEvidence]:
    """Extract explicitly labelled active ingredients independently of list matches."""
    evidence: list[ActiveIngredientEvidence] = []

    for page in document.pages:
        lines = _semantic_lines(page.text or "")
        for index, line in enumerate(lines):
            if not has_active_marker(line):
                continue
            evidence.extend(
                _extract_block(lines, index, document.file_name, page.page)
            )

    # Deduplicate repeated product headers/blocks while preserving the strongest
    # available concentration/CAS and the first page where the ingredient was
    # explicitly identified.
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
