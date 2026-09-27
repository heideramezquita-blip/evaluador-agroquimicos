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
    r"(?:%(?:\s*(?:w/w|w/v|v/v|p/p|p/v))?|"
    r"g\s*/\s*(?:litros?|kg|l)|mg\s*/\s*(?:litros?|kg|l)|"
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


_NARRATIVE_ACTIVE_PATTERNS = (
    re.compile(
        r"(?i)\btiene\s+como\s+ingrediente\s+activo\s+"
        r"(?P<name>[a-záéíóúüñ0-9][a-záéíóúüñ0-9 .,'’()/-]{1,120}?)"
        r"(?=\s+en\s+forma\s+de\b|\s+en\s+una\s+concentraci[oó]n\b|"
        r"\s+a\s+una\s+concentraci[oó]n\b|[.;]|$)"
    ),
    re.compile(
        r"(?i)\bel\s+ingrediente\s+activo\s+es\s+"
        r"(?P<name>[a-záéíóúüñ0-9][a-záéíóúüñ0-9 .,'’()/-]{1,120}?)"
        r"(?=\s+en\s+forma\s+de\b|\s+en\s+una\s+concentraci[oó]n\b|"
        r"\s+a\s+una\s+concentraci[oó]n\b|[.;]|$)"
    ),
)

_NARRATIVE_CONCENTRATION = re.compile(
    r"(?i)\b(?:en|a)\s+una\s+concentraci[oó]n\s+de\s+"
    r"(\d+(?:[.,]\d+)?\s*(?:%|g\s*/\s*(?:litros?|kg|l)|"
    r"mg\s*/\s*(?:litros?|kg|l)|kg\s*/\s*(?:l|ha)))"
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


_COMPOSITION_TABLE_HEADERS = (
    "no cas",
    "numero cas",
    "cas",
    "nombre",
    "simbolo de peligro",
    "riesgos especiales",
    "concentracion",
)


def _looks_like_composition_table(lines: list[str]) -> bool:
    """Recognize a table header following an explicit active-ingredient label."""
    keys = [match_key(line) for line in lines[:8]]
    header_hits = {
        header
        for header in _COMPOSITION_TABLE_HEADERS
        if any(key == header or key.startswith(header + " ") for key in keys)
    }
    return len(header_hits) >= 2 and any(
        header in header_hits for header in ("cas", "no cas", "numero cas")
    )


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

    prefixes = (
        _FIELD_PREFIXES
        + _STOP_PREFIXES
        + _NAME_VALUE_PREFIXES
        + _COMPOSITION_TABLE_HEADERS
    )
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


def _extract_narrative_active_identity(
    text: str,
    source_file: str,
    page_number: int,
) -> list[ActiveIngredientEvidence]:
    """Extract only high-confidence declarative active-ingredient sentences.

    Some technical sheets do not use an "Ingrediente activo:" field. They
    instead make a direct statement such as "tiene como ingrediente activo
    glifosato ...". These declarations are stronger than a generic narrative
    mention and can support documentary identity without opening a broad prose
    window.
    """
    cleaned = _clean_visible_text(text)
    evidence: list[ActiveIngredientEvidence] = []
    seen: set[str] = set()

    for pattern in _NARRATIVE_ACTIVE_PATTERNS:
        for match in pattern.finditer(cleaned):
            name = _strip_concentration(match.group("name"))
            key = match_key(name)
            if not key or key in seen or not _looks_like_name(name):
                continue

            tail = cleaned[match.end() : match.end() + 180]
            concentration_match = _NARRATIVE_CONCENTRATION.search(tail)
            concentration = (
                concentration_match.group(1).strip()
                if concentration_match
                else ""
            )
            cas_values = _valid_cas_in_text(
                cleaned[max(0, match.start() - 80) : match.end() + 220]
            )
            cas = cas_values[0] if len(cas_values) == 1 else ""

            seen.add(key)
            evidence.append(
                ActiveIngredientEvidence(
                    name=name,
                    source_file=source_file,
                    page=page_number,
                    concentration=concentration,
                    cas=cas,
                    context=cleaned[
                        max(0, match.start() - 80) : min(
                            len(cleaned), match.end() + 220
                        )
                    ],
                )
            )

    return evidence


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


def _candidate_tuples(
    lines: list[str],
    metadata_text: str = "",
) -> list[tuple[str, str, str]]:
    candidates: list[tuple[str, str, str]] = []

    for line in lines:
        if _is_stop(line):
            break

        orphan_concentration = _extract_concentration(line)
        orphan_cas_values = _valid_cas_in_text(line)
        stripped_orphan = _strip_concentration(line)
        if candidates and orphan_concentration and not _looks_like_name(stripped_orphan):
            name, concentration, cas = candidates[-1]
            candidates[-1] = (
                name,
                concentration or orphan_concentration,
                cas or (orphan_cas_values[0] if len(orphan_cas_values) == 1 else ""),
            )
            continue

        field_value = _field_value_candidate(line)
        candidate_line = field_value or line
        if not field_value and _is_field_line(candidate_line):
            continue

        for part in _split_candidate_line(candidate_line):
            parsed_part = part
            concentration = _extract_concentration(part)

            # Composition rows frequently use "Teflubenzuron: 150 g/L ...".
            # Treat only the short field before ':' as the identity when the
            # remainder contains a concentration. Structural labels such as
            # "Nombre químico:" were already excluded above.
            if ":" in part and concentration:
                prefix = part.split(":", 1)[0].strip()
                if 1 <= len(match_key(prefix).split()) <= 6:
                    parsed_part = prefix

            if not _looks_like_name(parsed_part):
                continue

            name = _strip_concentration(parsed_part)
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
        if metadata_text:
            block_text = f"{block_text} | {metadata_text}"
        if not concentration:
            concentration = _extract_concentration(block_text)
        if not cas:
            block_cas = _valid_cas_in_text(block_text)
            cas = block_cas[0] if len(block_cas) == 1 else ""
        candidates[0] = (name, concentration, cas)

    return candidates


def _contains_stop_field(lines: list[str]) -> bool:
    return any(_is_stop(line) for line in lines)


def _metadata_values(lines: list[str]) -> tuple[str, str]:
    """Extract concentration/CAS from structural metadata without creating names."""
    text = " | ".join(lines)
    concentration = _extract_concentration(text)
    cas_values = _valid_cas_in_text(text)
    cas = cas_values[0] if len(cas_values) == 1 else ""
    return concentration, cas


def _truncate_after_active_label(lines: list[str]) -> list[str]:
    """Keep only identity payload inside the label block.

    A PDF block may contain "Ingredientes activos: X" followed immediately by
    another structural field such as "Nombre químico:". Do not let the next
    field become part of the active-ingredient window.
    """
    payload: list[str] = []
    found = False

    for line in lines:
        if not found:
            tail = _active_label_tail(line)
            if tail is None:
                continue
            found = True
            if tail:
                payload.append(tail)
            continue

        if _starts_structural_field([line]) or _is_stop(line):
            break
        payload.append(line)

    return payload


def _horizontal_overlap(a: PdfTextBlock, b: PdfTextBlock) -> float:
    overlap = max(0.0, min(a.x1, b.x1) - max(a.x0, b.x0))
    width = max(1.0, min(a.x1 - a.x0, b.x1 - b.x0))
    return overlap / width


def _same_column(label: PdfTextBlock, candidate: PdfTextBlock) -> bool:
    return (
        _horizontal_overlap(label, candidate) >= 0.45
        or abs(label.x0 - candidate.x0) <= 36
    )


def _block_window(
    blocks: list[PdfTextBlock],
    label_index: int,
) -> tuple[list[str], str, str]:
    label = blocks[label_index]
    label_lines = _semantic_lines(label.text)
    payload = _truncate_after_active_label(label_lines)
    inline_candidates = _candidate_tuples(payload)

    aligned_texts = [label.text]
    metadata_parts: list[str] = []
    max_bottom = label.y1 + 180

    # If the label block already contains a usable identity (common in web
    # tables and compact FT layouts), do not absorb generic neighbouring text.
    # Only scan nearby structural blocks to enrich concentration/CAS.
    identity_found = bool(inline_candidates)
    fallback_payload: list[str] = []
    concentration_payload: list[str] = []

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

        if _active_label_tail(lines[0]) is not None:
            break

        structural = _starts_structural_field(lines)
        stop_field = _contains_stop_field(lines)

        if structural:
            aligned_texts.append(candidate.text)
            concentration, cas = _metadata_values(lines)
            if concentration or cas or _looks_like_composition_table(lines):
                metadata_parts.append(_clean_visible_text(candidate.text))
                max_bottom = max(max_bottom, candidate.y1 + 70)
                continue
            # A new non-metadata structural field ends the identity area.
            if identity_found:
                break
            continue

        if stop_field:
            # "C.s.p. 1 L | Ingredientes aditivos:" is a single extracted
            # block in some FT files. The additive marker terminates the active
            # ingredient area; preceding text in that block is not an active.
            break

        if identity_found:
            # Identity is already explicit in the label block. Ignore generic
            # nearby prose/catalog text; only structural metadata above may
            # enrich it.
            continue

        block_candidates = _candidate_tuples(lines)
        if not block_candidates:
            continue

        aligned_texts.append(candidate.text)
        if any(item[1] for item in block_candidates):
            # In two-column/table PDFs, non-identity text may be interleaved
            # before the real composition row. A concentration-bearing row is
            # materially stronger, so prefer only those parsed identities over
            # earlier loose candidates such as "Aspecto" / "Polvo blanco".
            for name, concentration, cas in block_candidates:
                if not concentration:
                    continue
                reconstructed = f"{name} {concentration}"
                if cas:
                    reconstructed += f" {cas}"
                concentration_payload.append(reconstructed)
            identity_found = True
            max_bottom = max(max_bottom, candidate.y1 + 70)
        elif not fallback_payload:
            fallback_payload.extend(lines)

    if not inline_candidates:
        payload = concentration_payload or fallback_payload

    return (
        payload,
        " | ".join(_clean_visible_text(x) for x in aligned_texts),
        " | ".join(metadata_parts),
    )


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

        payload, context, metadata_text = _block_window(blocks, block_index)
        candidates = _candidate_tuples(payload, metadata_text=metadata_text)

        if len(candidates) == 1 and metadata_text:
            name, concentration, cas = candidates[0]
            metadata_concentration, metadata_cas = _metadata_values(
                _semantic_lines(metadata_text)
            )
            candidates[0] = (
                name,
                concentration or metadata_concentration,
                cas or metadata_cas,
            )

        evidence.extend(
            _evidence_from_candidates(
                candidates,
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

        # Some FT files declare the active ingredient in a direct sentence
        # rather than a field/table. This path is deliberately narrow and only
        # accepts explicit declarative phrasing.
        evidence.extend(
            _extract_narrative_active_identity(
                page.text or "",
                document.file_name,
                page.page,
            )
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
