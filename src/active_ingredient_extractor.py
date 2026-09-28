from __future__ import annotations

import re

from .cas_utils import CAS_PATTERN, canonicalize_groups, extract_valid_cas, is_valid_cas
from .context_classifier import has_active_marker, has_composition_marker
from .models import ActiveIngredientEvidence, PdfDocument, PdfTextBlock
from .text_utils import clean_visible_text, match_key, normalize_text, semantic_lines


_ACTIVE_LABEL_PATTERNS = (
    re.compile(
        r"(?i)^\s*nombre\s+(?:del\s+)?ingrediente\s*"
        r"(?:\(s\)|s|\s+s)?\s*activo\s*(?:\(s\)|s|\s+s)?\s*:?\s*(.*)$"
    ),
    re.compile(
        r"(?i)^\s*ingrediente\s*(?:\(s\)|s|\s+s)?\s*"
        r"activo\s*(?:\(s\)|s|\s+s)?\s*:?\s*(.*)$"
    ),
    re.compile(
        r"(?i)^\s*principio\s*(?:\(s\)|s|\s+s)?\s+"
        r"activo\s*(?:\(s\)|s|\s+s)?\s*:?\s*(.*)$"
    ),
    re.compile(
        r"(?i)^\s*active\s+ingredient\s*(?:\(s\)|s|\s+s)?\s*:?\s*(.*)$"
    ),
    re.compile(r"(?i)^\s*i\s*\.?\s*a\s*\.?(?=\s|:|$)\s*:?\s*(.*)$"),
)

_CONCENTRATION_UNIT = (
    r"%(?:\s*(?:p(?:/p|/v)?|w/w|w/v|v/v|p/p|p/v))?|"
    r"g\s*/\s*(?:litros?|kg|l)|mg\s*/\s*(?:litros?|kg|l)|"
    r"kg\s*/\s*l|g\s+l-?1|g\s+kg-?1"
)

_CONCENTRATION = re.compile(
    rf"(?i)(\d+(?:[.,]\d+)?\s*(?:{_CONCENTRATION_UNIT}))"
)

_CONCENTRATION_SERIES = re.compile(
    rf"(?i)(?P<values>\d+(?:[.,]\d+)?"
    rf"(?:\s*\+\s*\d+(?:[.,]\d+)?)+)\s*"
    rf"(?P<unit>{_CONCENTRATION_UNIT})"
)


_APPLICATION_RATE = re.compile(
    r"(?i)\b\d+(?:[.,]\d+)?"
    r"(?:\s*(?:a|-)\s*\d+(?:[.,]\d+)?)?\s*"
    r"(?:kg|g|l|ml)\s*/\s*ha\b"
)

_STOP_PREFIXES = (
    "ingrediente aditivo",
    "ingredientes aditivos",
    "ingrediente inerte",
    "ingredientes inertes",
    "aditivo",
    "aditivos",
    "otros ingredientes",
    "otras sustancias",
    "categoria toxicologica",
    "categoria",
    "presentacion",
    "grupo",
    "grupo quimico",
    "modo de accion",
    "modo de aplicacion",
    "mecanismo de accion",
    "generalidades",
    "compatibilidad",
    "compatibilidad y fitotoxicidad",
    "fitotoxicidad",
    "compatibility",
    "beneficios",
    "cultivos",
    "blancos biologicos",
    "objetivo biologico",
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
    "uso general",
    "uso recomendado",
    "componentes",
    "componentes peligrosos",
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
    "grupo",
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


_IUPAC_IA_FIELD = re.compile(
    r"(?i)^\s*nombre\s+iupac\s*\(\s*i\s*\.?\s*a\s*\.?\s*\)\s*:?\s*(.*)$"
)

_OTHER_IDENTIFIER_FIELD = re.compile(
    r"(?i)^\s*(?:\d+(?:\.\d+)?\s*)?otros\s+medios\s+de\s+"
    r"identificaci[oó]n\s*:\s*(.+)$"
)

_CHEMICAL_SALT_IDENTIFIER = re.compile(
    r"(?i)^\s*sal\s+[A-Za-zÁÉÍÓÚÜÑáéíóúüñ-]{2,30}\s+de\s+"
    r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9][A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9 .,'’()/-]{1,80}\.?\s*$"
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
    re.compile(
        r"(?i)\bel\s+ingrediente\s+activo\s+"
        r"(?!(?:es|se|tiene|presenta|puede|fue|ha|resulta)\b)"
        r"(?P<name>[a-záéíóúüñ][a-záéíóúüñ0-9 .,'’()/-]{1,80}?)"
        r"\s+es\b"
    ),
)

_NARRATIVE_CONCENTRATION = re.compile(
    r"(?i)\b(?:en|a)\s+una\s+concentraci[oó]n\s+de\s+"
    r"(\d+(?:[.,]\d+)?\s*(?:%|g\s*/\s*(?:litros?|kg|l)|"
    r"mg\s*/\s*(?:litros?|kg|l)|kg\s*/\s*(?:l|ha)))"
)


_NARRATIVE_SALT_FORM = re.compile(
    r"(?i)^\s*en\s+forma\s+de\s+"
    r"(?P<form>sal\s+[a-záéíóúüñ-]{2,30})"
    r"(?=\s+(?:en|a)\s+una\s+concentraci[oó]n\b|[.;]|$)"
)


def _active_label_tail(line: str) -> str | None:
    """Return label tail only for an explicit field-style active label.

    Narrative sentences such as "a base de los ingredientes activos X e Y"
    are deliberately ignored. They may corroborate identity, but must not
    open an extraction window that absorbs surrounding prose.
    """
    cleaned = clean_visible_text(line)
    for pattern in _ACTIVE_LABEL_PATTERNS:
        match = pattern.match(cleaned)
        if match:
            tail = match.group(1).strip(" :-/|")
            tail_key = match_key(tail)
            # A bare sentence fragment such as "ingrediente activo." is not
            # a field label. Treating it as one can open an extraction window
            # into unrelated toxicology/ecotoxicology prose. Punctuation-only
            # tails normalize to an empty semantic key.
            if not tail_key and cleaned.rstrip().endswith((".", ";")):
                return None
            if (
                "identificador del producto" in tail_key
                or tail_key.startswith("nombre identificador")
                or tail_key.startswith("nombre cas")
            ):
                return ""

            # A PDF line break can make a narrative phrase look like a
            # field-style label, e.g.:
            #   "Tiene dos"
            #   "ingredientes activos especialistas en lepidópteros..."
            # Such prose must not create synthetic active ingredients.
            narrative_tail_prefixes = (
                "especialistas en",
                "responsables de",
                "destinados a",
                "utilizados para",
                "usados para",
                "en el producto",
                "en la formulacion",
                "grado tecnico",
                "que ",
            )
            if any(
                tail_key.startswith(prefix)
                for prefix in narrative_tail_prefixes
            ):
                return None
            return tail
    return None


def _is_contextual_active_reference(lines: list[str], index: int) -> bool:
    """Reject active-marker text that belongs to a surrounding prose label."""
    preceding = match_key(" ".join(lines[max(0, index - 2) : index]))
    return any(
        preceding.endswith(prefix)
        for prefix in (
            "compatibilidad con",
            "compatible con",
            "compatibilidad con los",
            "mezcla con",
            "tiene dos",
            "tiene 2",
            "contiene dos",
            "contiene 2",
            "posee dos",
            "posee 2",
            "presenta dos",
            "presenta 2",
        )
    )


def _active_label_span_at(
    lines: list[str],
    index: int,
) -> tuple[int, str] | None:
    """Return (exclusive end index, tail) for a field-style active label."""
    if _is_contextual_active_reference(lines, index):
        return None

    for size in range(1, min(3, len(lines) - index) + 1):
        combined = " ".join(lines[index : index + size])
        tail = _active_label_tail(combined)
        if tail is not None:
            return index + size, tail
    return None


def _find_active_label_span(
    lines: list[str],
) -> tuple[int, int, str] | None:
    for index in range(len(lines)):
        span = _active_label_span_at(lines, index)
        if span is None:
            continue
        end_index, tail = span
        return index, end_index, tail
    return None


def _is_stop(line: str) -> bool:
    cleaned = clean_visible_text(line)
    key = match_key(cleaned)
    if any(key.startswith(prefix) for prefix in _STOP_PREFIXES):
        return True
    if re.fullmatch(r"(?:seccion\s*)?\d{1,2}\s+[a-z].*", key):
        return True
    # Numbered SDS/FT subsections such as "1.2. Usos pertinentes..." are
    # structural boundaries, not ingredient names. Inspect the visible
    # punctuation so pesticide names such as 2,4-D are not misclassified.
    if re.match(
        r"^\s*\d{1,2}\.\d{1,2}\.?\s+[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]",
        cleaned,
    ):
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


def _format_concentration(value: str, unit: str) -> str:
    unit = re.sub(r"\s+", "", unit.strip())
    return f"{value}{unit}" if unit.startswith("%") else f"{value} {unit}"


def _extract_concentration_series(text: str) -> list[str]:
    """Return ordered concentration values, including shared-unit series.

    Technical sheets often declare several active ingredients in one field and
    their concentrations in a parallel expression such as
    "262.5 + 87.5 g/L". The unit applies to both values, so treating only the
    final "87.5 g/L" as the concentration loses the one-to-one relationship.
    """
    value = text or ""
    series = _CONCENTRATION_SERIES.search(value)
    if series:
        values = [
            part.strip()
            for part in re.split(r"\s*\+\s*", series.group("values"))
            if part.strip()
        ]
        unit = series.group("unit")
        return [_format_concentration(item, unit) for item in values]

    concentrations: list[str] = []
    for match in _CONCENTRATION.finditer(value):
        item = match.group(1).strip()
        if item not in concentrations:
            concentrations.append(item)
    return concentrations


def _strip_concentration(line: str) -> str:
    value = _CONCENTRATION.sub(" ", line or "")
    value = CAS_PATTERN.sub(" ", value)
    value = re.sub(r"(?i)\b(?:n[uú]mero\s+)?cas\b\s*[:#-]?", " ", value)
    value = re.sub(r"(?i)\(\s*formulaci[oó]n[^)]*\)", " ", value)
    value = re.sub(r"\.{3,}", " ", value)
    value = re.sub(r"\(\s*\)", " ", value)
    value = re.sub(r"\s*\+\s*$", " ", value)
    value = re.sub(r"\s*[/|;,]+\s*$", " ", value)
    return re.sub(r"\s+", " ", value).strip(" :-/|;,.+()")


def _is_toxicology_endpoint(line: str) -> bool:
    """Return whether a line is a toxicology/ecotoxicology test endpoint."""
    key = match_key(clean_visible_text(line))
    if not key:
        return False
    if re.match(
        r"^(?:cl|lc|dl|ld|ce|ec)\s*50\b|"
        r"^(?:noael|noel|lo(?:a)?el|noec|loec)\b",
        key,
    ):
        return True

    organism_prefixes = (
        "peces",
        "pez",
        "trucha",
        "aves",
        "pato",
        "abejas",
        "abeja",
        "crustaceos",
        "daphnia",
        "algas",
        "alga",
        "lombriz",
        "lombrices",
        "organismos acuaticos",
        "organismos terrestres",
    )
    endpoint_markers = (
        " cl50",
        " lc50",
        " dl50",
        " ld50",
        " ce50",
        " ec50",
        " noael",
        " noel",
        " noec",
        " loec",
    )
    return any(key.startswith(prefix) for prefix in organism_prefixes) and any(
        marker in f" {key}" for marker in endpoint_markers
    )


def _looks_like_name(line: str) -> bool:
    value = _strip_concentration(clean_visible_text(line))
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

    # Structural/table tokens and agronomic abbreviations are not chemical
    # identities. These commonly appear next to active-ingredient tables and
    # can otherwise survive generic name heuristics after PDF cell splitting.
    non_identity_tokens = {
        "ingrediente",
        "ingredientes",
        "activo",
        "activos",
        "aditivo",
        "aditivos",
        "p r",
        "p c",
        "n a",
        "pr",
        "pc",
        "na",
        "version",
        "revision",
        "sds",
    }
    if key in non_identity_tokens:
        return False

    words = key.split()
    if len(words) > 12 or len(value) > 120:
        return False
    # Truncated systematic-name fragments created by PDF line wrapping are
    # not standalone ingredient identities (e.g. "methyl 2").
    if re.fullmatch(r"[a-z]{2,20}\s+\d+", key):
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
        "las semividas de degradacion",
        "semividas de degradacion",
        "el producto es toxico",
        "producto es toxico",
        "toxico para aves",
        "toxicidad para los",
        "tiempo de exposicion",
        "estimacion basada en datos",
    )
    normalized = normalize_text(value)
    if any(marker in normalized for marker in prose_markers):
        return False

    # GHS hazard-classification cells are not chemical identities. In complex
    # SDS tables the concentration cell can be visually adjacent to
    # "Acute Tox. 4; Aquatic Acute 1; ..." and older parsing could promote
    # that classification text to an ingredient name.
    hazard_prefixes = (
        "acute tox",
        "aquatic acute",
        "aquatic chronic",
        "skin irrit",
        "skin sens",
        "eye irrit",
        "eye dam",
        "carc ",
        "muta ",
        "reprod ",
        "stot ",
        "asp tox",
        "flamm liq",
    )
    if any(key.startswith(prefix) for prefix in hazard_prefixes):
        return False
    if re.match(r"^(?:h\d{3}|p\d{3}|[<>]=?)\b", value.strip(), re.I):
        return False

    # Toxicology/ecotoxicology endpoints describe test results, not chemical
    # identities. They often appear immediately after a bare "Ingrediente
    # activo" heading in SDS tables and can carry concentration-like units.
    if _is_toxicology_endpoint(value):
        return False

    # Repeated document metadata in page headers/footers is never chemistry.
    if key.startswith(("version ", "revision ", "fecha de revision ", "sds ")):
        return False

    # Physical-appearance values belong to product-properties panels, not to
    # chemical identity. This prevents two-panel layouts from promoting values
    # such as "Polvo blanco" when the true active row is nearby.
    physical_form_prefixes = (
        "polvo ",
        "liquido ",
        "solido ",
        "granulo ",
        "granulos ",
        "suspension ",
        "emulsion ",
        "gel ",
    )
    if any(key.startswith(prefix) for prefix in physical_form_prefixes):
        return False
    return True


def _compact_common_name(value: str) -> str:
    """Recover the short common name from a long chemical-name cell.

    Some SDS tables place a common pesticide name followed by a long systematic
    name in parentheses. When the full cell is too long to be a safe identity,
    the short prefix is still useful if it is syntactically name-like.
    """
    cleaned = clean_visible_text(value)
    for separator in ("(", ","):
        if separator in cleaned:
            prefix = cleaned.split(separator, 1)[0].strip(" :-/|;,.")
            if 1 <= len(match_key(prefix).split()) <= 6 and _looks_like_name(prefix):
                return prefix
    return ""


def _extract_iupac_ia_identity(
    text: str,
    source_file: str,
    page_number: int,
) -> list[ActiveIngredientEvidence]:
    """Extract identity from fields explicitly labelled Nombre IUPAC (I.A)."""
    lines = semantic_lines(text)
    evidence: list[ActiveIngredientEvidence] = []

    for index, line in enumerate(lines):
        match = _IUPAC_IA_FIELD.match(line)
        if not match:
            continue

        value = match.group(1).strip()
        cursor = index + 1
        if not value and cursor < len(lines):
            value = lines[cursor]
            cursor += 1

        # These documents put the pesticide common name before the systematic
        # IUPAC description, separated by a comma.
        common_name = value.split(",", 1)[0].strip(" :-/|;,.")
        if not _looks_like_name(common_name):
            continue

        window = " | ".join(lines[index : min(len(lines), index + 8)])
        cas_values = extract_valid_cas(window)
        cas = cas_values[0] if len(cas_values) == 1 else ""

        evidence.append(
            ActiveIngredientEvidence(
                name=clean_visible_text(common_name),
                source_file=source_file,
                page=page_number,
                concentration="",
                cas=cas,
                context=window,
            )
        )

    return evidence


def _extract_other_identifier_identity(
    text: str,
    source_file: str,
    page_number: int,
) -> list[ActiveIngredientEvidence]:
    """Use only narrowly chemical alternative identifiers as product identity.

    "Otros medios de identificación" is broad in SDS documents, so it is not
    generally promoted to active-ingredient evidence. A short salt-of-substance
    phrase (e.g. "sal amonio de glifosato") is sufficiently chemical and
    product-specific to expose documentary identity without relying on OCR.
    """
    evidence: list[ActiveIngredientEvidence] = []
    for line in semantic_lines(text):
        match = _OTHER_IDENTIFIER_FIELD.match(line)
        if not match:
            continue
        value = match.group(1).strip(" :-/|;,.")
        if not _CHEMICAL_SALT_IDENTIFIER.fullmatch(value):
            continue
        evidence.append(
            ActiveIngredientEvidence(
                name=clean_visible_text(value),
                source_file=source_file,
                page=page_number,
                concentration="",
                cas="",
                context=line,
            )
        )
    return evidence


def _extract_correlated_sds_identifier_identity(
    document: PdfDocument,
) -> list[ActiveIngredientEvidence]:
    """Confirm a pesticide active identity from two independent SDS statements.

    Some SDS files do not use the literal label "Ingrediente activo". Instead,
    section 1 names a short chemical under "Otros medios de identificación"
    and a later product-characterization field gives a concentration explicitly
    "de <same chemical>". When the document also states an agricultural
    pesticide use, those two independent statements are sufficiently specific
    to establish the product's active chemical identity without promoting
    arbitrary composition rows or toxicology references.

    Example observed in KUNFU 100 EC:
        1.2 Otros medios de identificación: bifentrina.
        Uso recomendado: insecticida para uso agrícola.
        Concentración: 100 g/L de bifentrina.
    """
    identifiers: list[tuple[str, int, str]] = []
    pesticide_use = False

    for page in document.pages:
        for line in semantic_lines(page.text or ""):
            line_key = match_key(line)
            if any(
                cue in line_key
                for cue in (
                    "insecticida para uso agricola",
                    "herbicida para uso agricola",
                    "fungicida para uso agricola",
                    "acaricida para uso agricola",
                    "plaguicida para uso agricola",
                    "insecticida de uso agricola",
                    "herbicida de uso agricola",
                    "fungicida de uso agricola",
                    "acaricida de uso agricola",
                )
            ):
                pesticide_use = True

            match = _OTHER_IDENTIFIER_FIELD.match(line)
            if not match:
                continue
            value = match.group(1).strip(" :-/|;,.")
            key = match_key(value)
            if (
                not key
                or len(key.split()) > 6
                or not _looks_like_name(value)
            ):
                continue
            identifiers.append((clean_visible_text(value), page.page, line))

    if not pesticide_use or not identifiers:
        return []

    evidence: list[ActiveIngredientEvidence] = []
    seen: set[str] = set()

    for identifier, identifier_page, identifier_line in identifiers:
        identifier_key = match_key(identifier)
        for page in document.pages:
            lines = semantic_lines(page.text or "")
            for line in lines:
                key = match_key(line)
                if not key.startswith("concentracion "):
                    continue

                concentration = _extract_concentration(line)
                if not concentration:
                    continue

                # Require an explicit "de <identifier>" relation in this same
                # field so generic concentration data cannot establish identity.
                relation = re.search(
                    r"(?i)\bde\s+(.+?)\s*[.;]?$",
                    clean_visible_text(line),
                )
                if not relation:
                    continue
                named = relation.group(1).strip(" :-/|;,.")
                if match_key(named) != identifier_key:
                    continue

                if identifier_key in seen:
                    continue
                seen.add(identifier_key)
                evidence.append(
                    ActiveIngredientEvidence(
                        name=identifier,
                        source_file=document.file_name,
                        page=identifier_page,
                        concentration=concentration,
                        cas="",
                        context=(
                            f"{identifier_line} | "
                            f"{clean_visible_text(line)}"
                        ),
                    )
                )

    return evidence


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
    cleaned = clean_visible_text(text)
    evidence: list[ActiveIngredientEvidence] = []
    seen: set[str] = set()

    for pattern in _NARRATIVE_ACTIVE_PATTERNS:
        for match in pattern.finditer(cleaned):
            name = _strip_concentration(match.group("name"))
            tail = cleaned[match.end() : match.end() + 180]

            # Preserve the explicitly declared salt form as part of the active
            # ingredient identity. In product sheets such as Panzer K / Panzer
            # 747, "glifosato en forma de sal potasio/amoniacal" is one
            # ingredient identity, not two ingredients.
            salt_match = _NARRATIVE_SALT_FORM.match(tail)
            if salt_match:
                name = (
                    f"{name} en forma de "
                    f"{clean_visible_text(salt_match.group('form'))}"
                )

            key = match_key(name)
            if not key or key in seen or not _looks_like_name(name):
                continue

            concentration_match = _NARRATIVE_CONCENTRATION.search(tail)
            concentration = (
                concentration_match.group(1).strip()
                if concentration_match
                else ""
            )
            cas_values = extract_valid_cas(
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


_PAIRED_ACTIVE_CONCENTRATIONS = re.compile(
    r"(?i)^\s*(?P<names>.+?)\s*/\s*"
    r"(?P<values>\d+(?:[.,]\d+)?(?:\s*\+\s*\d+(?:[.,]\d+)?)+)\s*"
    r"(?P<unit>%|g\s*/\s*(?:kg|l|litros?)|mg\s*/\s*(?:kg|l|litros?))\s*$"
)

_UNIT_ONLY = re.compile(
    r"(?i)^\s*(?:g|mg|kg)\s*/\s*(?:kg|l|litros?)\s*$"
)
_TRAILING_NUMBER = re.compile(r"\d+(?:[.,]\d+)?\s*$")


def _paired_active_concentrations(
    line: str,
) -> list[tuple[str, str, str]]:
    match = _PAIRED_ACTIVE_CONCENTRATIONS.fullmatch(clean_visible_text(line))
    if not match:
        return []

    names = [
        part.strip(" :-/|;,.+")
        for part in re.split(r"\s+\+\s+", match.group("names"))
        if part.strip()
    ]
    values = [
        part.strip()
        for part in re.split(r"\s*\+\s*", match.group("values"))
        if part.strip()
    ]
    if len(names) < 2 or len(names) != len(values):
        return []
    if not all(_looks_like_name(name) for name in names):
        return []

    unit = re.sub(r"\s+", "", match.group("unit"))
    return [
        (clean_visible_text(name), f"{value} {unit}", "")
        for name, value in zip(names, values)
    ]


def _coalesce_split_concentration_lines(lines: list[str]) -> list[str]:
    """Join rows where PDF extraction split name/number/unit across lines."""
    merged: list[str] = []
    index = 0

    while index < len(lines):
        if (
            index + 2 < len(lines)
            and _TRAILING_NUMBER.search(lines[index + 1])
            and _UNIT_ONLY.fullmatch(lines[index + 2])
            and _looks_like_name(lines[index])
        ):
            combined = (
                f"{lines[index]} {lines[index + 1]} {lines[index + 2]}"
            )
            if _extract_concentration(combined):
                merged.append(combined)
                index += 3
                continue

        if (
            index + 1 < len(lines)
            and _TRAILING_NUMBER.search(lines[index])
            and _UNIT_ONLY.fullmatch(lines[index + 1])
        ):
            combined = f"{lines[index]} {lines[index + 1]}"
            if _extract_concentration(combined):
                merged.append(combined)
                index += 2
                continue

        merged.append(lines[index])
        index += 1

    return merged


def _split_candidate_line(line: str) -> list[str]:
    """Split explicit multi-active names written with '+'.

    Product sheets frequently omit spaces around the separator
    (e.g. "IMAZAPIC+IMAZAPYR"). Split only when every resulting part still
    looks like a chemical/common-name identity; this avoids treating numeric
    concentration series as ingredient names.
    """
    cleaned = clean_visible_text(line)
    if "+" not in cleaned:
        return [cleaned] if cleaned else []

    parts = [
        part.strip(" :-/|;,.+")
        for part in re.split(r"\s*\+\s*", cleaned)
        if part.strip(" :-/|;,.+")
    ]
    if len(parts) >= 2 and all(_looks_like_name(part) for part in parts):
        return parts
    return [cleaned] if cleaned else []


def _candidate_tuples(
    lines: list[str],
    metadata_text: str = "",
) -> list[tuple[str, str, str]]:
    candidates: list[tuple[str, str, str]] = []
    lines = _coalesce_split_concentration_lines(lines)
    systematic_description_open = False
    equivalence_description_open = False

    for line in lines:
        if _is_stop(line):
            break

        line_key = match_key(line)

        # Equivalence/salt wording inside an active-ingredient declaration
        # describes the already identified active rather than introducing a
        # second ingredient. Example:
        #   Glifosato 680 g/kg
        #   N-(phosphonomethyl) glycine, equivalente a 747 g/kg de Glyphosate
        #   Monoammonium salt, de formulacion a 20 C
        # Keep the labelled common name and its formulation concentration.
        if candidates and (
            "equivalente a" in line_key
            or "equivalent to" in line_key
            or "acid equivalent" in line_key
        ):
            equivalence_description_open = True
            continue

        if equivalence_description_open:
            descriptive_markers = (
                " salt",
                "sal ",
                "de formulacion",
                "formulacion a",
                "formulation",
            )
            padded_key = f" {line_key} "
            if any(marker in padded_key for marker in descriptive_markers):
                continue
            equivalence_description_open = False

        orphan_concentration = _extract_concentration(line)
        orphan_cas_values = extract_valid_cas(line)
        stripped_orphan = _strip_concentration(line)
        if candidates and orphan_concentration and not _looks_like_name(stripped_orphan):
            name, concentration, cas = candidates[-1]
            candidates[-1] = (
                name,
                concentration or orphan_concentration,
                cas or (orphan_cas_values[0] if len(orphan_cas_values) == 1 else ""),
            )
            continue

        paired = _paired_active_concentrations(line)
        if paired:
            candidates.extend(paired)
            systematic_description_open = False
            continue

        # A common-name line can open a wrapped systematic/IUPAC description:
        #   Novaluron: 1-[3-cloro-4-(...)
        #   fenil]-3-(2,6-difluorobenzoil) urea.
        # Once the common name has been captured, the continuation is
        # descriptive chemistry, not a second active ingredient.
        if systematic_description_open and ":" not in line:
            if not _extract_concentration(line) and not extract_valid_cas(line):
                continue
            systematic_description_open = False

        field_value = _field_value_candidate(line)
        candidate_line = field_value or line
        if not field_value and _is_field_line(candidate_line):
            continue

        for part in _split_candidate_line(candidate_line):
            parsed_part = part
            concentration = _extract_concentration(part)

            # Composition rows frequently use "Teflubenzuron: 150 g/L ...".
            # A second pattern is "Novaluron: <long systematic name>", where
            # only the short common-name prefix is the active identity.
            # Structural labels such as "Nombre químico:" were excluded above.
            if ":" in part:
                prefix, suffix = part.split(":", 1)
                prefix = prefix.strip()
                suffix = suffix.strip()
                if 1 <= len(match_key(prefix).split()) <= 6 and _looks_like_name(prefix):
                    if concentration:
                        parsed_part = prefix
                    elif suffix and (
                        len(suffix) >= 18
                        or re.search(r"[\d\[\]()'-]", suffix)
                    ):
                        parsed_part = prefix
                        systematic_description_open = True

            if not _looks_like_name(parsed_part):
                compact = _compact_common_name(_strip_concentration(parsed_part))
                if not compact:
                    continue
                parsed_part = compact

            name = _strip_concentration(parsed_part)
            same_line_cas = extract_valid_cas(part)
            candidates.append(
                (
                    clean_visible_text(name),
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
            block_cas = extract_valid_cas(block_text)
            cas = block_cas[0] if len(block_cas) == 1 else ""
        candidates[0] = (name, concentration, cas)

    elif len(candidates) > 1 and metadata_text:
        concentrations = _extract_concentration_series(metadata_text)
        if (
            len(concentrations) == len(candidates)
            and all(not concentration for _, concentration, _ in candidates)
        ):
            candidates = [
                (name, concentrations[index], cas)
                for index, (name, _, cas) in enumerate(candidates)
            ]

    return candidates


def _contains_stop_field(lines: list[str]) -> bool:
    return any(_is_stop(line) for line in lines)


def _metadata_values(lines: list[str]) -> tuple[str, str]:
    """Extract concentration/CAS from structural metadata without creating names."""
    text = " | ".join(lines)
    concentration = _extract_concentration(text)
    cas_values = extract_valid_cas(text)
    cas = cas_values[0] if len(cas_values) == 1 else ""
    return concentration, cas


def _explicit_identity_block_concentration_text(lines: list[str]) -> str:
    """Return the concentration expression explicitly tied to an active field.

    Unlike the single-identity fallback below, this helper does not scan
    arbitrary trailing values. It only accepts an explicit Concentración/
    Contenido field, which makes ordered pairing safe for multi-active products.
    """
    span = _find_active_label_span(lines)
    if span is None:
        return ""

    _, end_index, _ = span
    trailing = lines[end_index:]
    for index, line in enumerate(trailing):
        key = match_key(line)
        if not (
            key.startswith("concentracion")
            or key.startswith("contenido")
        ):
            continue

        if _extract_concentration_series(line):
            return clean_visible_text(line)

        for candidate in trailing[index + 1 : index + 3]:
            if _starts_structural_field([candidate]) or _is_stop(candidate):
                break
            if _extract_concentration_series(candidate):
                return clean_visible_text(candidate)

    return ""


def _single_identity_block_concentration(lines: list[str]) -> str:
    """Recover one unambiguous concentration from the active-identity block.

    PDF table extraction can reorder cells inside a single block. Two observed
    patterns are:

        Ingrediente activo | Glifosato | Concentración | 480 g/L
        Ingrediente activo | Glifosato | Ingredientes aditivos | 480 g/L | c.s.p.

    The ordinary payload parser stops at structural/additive labels, which is
    correct for identity names but can hide the concentration. For a block that
    already yielded exactly one active identity, recover the concentration only
    when an explicit concentration field identifies it or when the entire
    trailing block contains exactly one concentration-like value.
    """
    span = _find_active_label_span(lines)
    if span is None:
        return ""

    _, end_index, _ = span
    trailing = lines[end_index:]
    if not trailing:
        return ""

    for index, line in enumerate(trailing):
        key = match_key(line)
        if not (
            key.startswith("concentracion")
            or key.startswith("contenido")
        ):
            continue

        value = _extract_concentration(line)
        if value:
            return value

        for candidate in trailing[index + 1 : index + 3]:
            if _starts_structural_field([candidate]) or _is_stop(candidate):
                break
            value = _extract_concentration(candidate)
            if value:
                return value

    values: list[str] = []
    for line in trailing:
        value = _extract_concentration(line)
        if value and value not in values:
            values.append(value)

    return values[0] if len(values) == 1 else ""


def _truncate_after_active_label(lines: list[str]) -> list[str]:
    """Keep only identity payload inside the label block."""
    span = _find_active_label_span(lines)
    if span is None:
        return []

    _, end_index, tail = span
    payload: list[str] = [tail] if tail else []

    for line in lines[end_index:]:
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
    label_lines = semantic_lines(label.text)
    span = _find_active_label_span(label_lines)
    payload = _truncate_after_active_label(label_lines)

    # A bare "Ingrediente activo" heading immediately followed by CL50/DL50/
    # EC50/NOEC etc. is an ecotoxicology subheading, not product identity.
    # Do not continue into a page footer/header looking for fallback names.
    if span is not None:
        _, end_index, tail = span
        if not tail and any(
            _is_toxicology_endpoint(line)
            for line in label_lines[end_index:]
        ):
            return [], clean_visible_text(label.text), ""

    inline_candidates = _candidate_tuples(payload)

    aligned_texts = [label.text]
    metadata_parts: list[str] = []

    if inline_candidates:
        explicit_concentration = _explicit_identity_block_concentration_text(
            label_lines
        )
        if explicit_concentration:
            metadata_parts.append(explicit_concentration)
        elif len(inline_candidates) == 1 and not inline_candidates[0][1]:
            inline_concentration = _single_identity_block_concentration(label_lines)
            if inline_concentration:
                metadata_parts.append(inline_concentration)

        # A compact SDS block can contain the active label, common name,
        # systematic name and "N° CAS del i.a." in one text block. Preserve a
        # unique validated CAS from that same block as metadata; do not assign
        # one CAS across multiple active candidates.
        if len(inline_candidates) == 1 and not inline_candidates[0][2]:
            inline_cas = extract_valid_cas(" | ".join(label_lines))
            if len(inline_cas) == 1:
                metadata_parts.append(f"CAS {inline_cas[0]}")

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

        lines = semantic_lines(candidate.text)
        if not lines:
            continue

        if _active_label_tail(lines[0]) is not None:
            break

        structural = _starts_structural_field(lines)
        stop_field = _contains_stop_field(lines)

        if structural:
            aligned_texts.append(candidate.text)

            first_key = match_key(lines[0])
            if first_key in {"nombre comun", "common name"} and len(lines) > 1:
                common_name_candidates = _candidate_tuples(lines[1:])
                concentration_bearing = [
                    item for item in common_name_candidates if item[1]
                ]
                if concentration_bearing:
                    for name, concentration, cas in concentration_bearing:
                        reconstructed = f"{name} {concentration}"
                        if cas:
                            reconstructed += f" {cas}"
                        concentration_payload.append(reconstructed)
                    identity_found = True
                    max_bottom = max(max_bottom, candidate.y1 + 70)
                    continue

            concentration, cas = _metadata_values(lines)
            if concentration or cas or _looks_like_composition_table(lines):
                metadata_parts.append(clean_visible_text(candidate.text))
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
            label_key = match_key(label.text)
            table_identity_header = has_active_marker(label.text) and any(
                cue in label_key
                for cue in (
                    "porcentaje",
                    "identificador del producto",
                    "concentracion",
                    "cas",
                )
            )
            if table_identity_header:
                concentration, cas = _metadata_values(lines)
                if concentration or cas:
                    metadata_parts.append(clean_visible_text(candidate.text))
                    max_bottom = max(max_bottom, candidate.y1 + 70)
            continue

        # A concentration may be extracted as its own visual row/cell. If so,
        # attach it to the nearest preceding candidate inside the same block.
        block_concentration = _extract_concentration(" | ".join(lines))
        if block_concentration and not any(item[1] for item in block_candidates):
            name, _, cas = block_candidates[-1]
            block_candidates[-1] = (name, block_concentration, cas)

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
        " | ".join(clean_visible_text(x) for x in aligned_texts),
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
        lines = semantic_lines(block.text)
        if _find_active_label_span(lines) is None:
            continue

        payload, context, metadata_text = _block_window(blocks, block_index)
        candidates = _candidate_tuples(payload, metadata_text=metadata_text)

        if len(candidates) == 1 and metadata_text:
            name, concentration, cas = candidates[0]
            metadata_concentration, metadata_cas = _metadata_values(
                semantic_lines(metadata_text)
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


def _merge_wrapped_name_lines(lines: list[str]) -> list[str]:
    merged: list[str] = []
    for line in lines:
        cleaned = clean_visible_text(line)
        if not cleaned:
            continue
        if merged and cleaned[:1].islower():
            merged[-1] = f"{merged[-1]} {cleaned}"
        else:
            merged.append(cleaned)
    return merged


def _vertical_overlap(a: PdfTextBlock, b: PdfTextBlock) -> float:
    overlap = max(0.0, min(a.y1, b.y1) - max(a.y0, b.y0))
    height = max(1.0, min(a.y1 - a.y0, b.y1 - b.y0))
    return overlap / height


def _candidate_belongs_to_nearby_field(
    candidate: PdfTextBlock,
    label: PdfTextBlock,
    blocks: list[PdfTextBlock],
) -> bool:
    """Reject a value cell owned by another nearby field in a parallel column.

    Two-column technical sheets can place an active-ingredient label at the
    same vertical position as an unrelated value such as "Por aspersión".
    Geometric overlap alone is therefore insufficient: if a nearby heading in
    the candidate's own column precedes it, that heading owns the value.
    """
    for possible_heading in blocks:
        if possible_heading is label or possible_heading is candidate:
            continue
        if possible_heading.y1 > candidate.y0 + 3:
            continue
        vertical_gap = candidate.y0 - possible_heading.y1
        if vertical_gap < 0 or vertical_gap > 42:
            continue
        if not _same_column(possible_heading, candidate):
            continue

        # A broad preceding table row can geometrically overlap both the
        # active-label cell and the value cell (e.g. INEX-A:
        # "Clasificación | Surfactante"). Such a row is not the owner of the
        # active-value cell. Only a heading that belongs to the candidate's
        # column without also substantially overlapping the active label may
        # claim that candidate. This preserves the SEROK safeguard where
        # "MODO DE APLICACIÓN" owns "Por aspersión".
        if _horizontal_overlap(possible_heading, label) >= 0.45:
            continue

        lines = semantic_lines(possible_heading.text)
        if not lines:
            continue
        if _starts_structural_field(lines) or _contains_stop_field(lines):
            return True
    return False


def _extract_right_column_active_identity(
    blocks: list[PdfTextBlock],
    source_file: str,
    page_number: int,
) -> list[ActiveIngredientEvidence]:
    """Extract active names from a value cell to the right of an explicit label."""
    for label in blocks:
        lines = semantic_lines(label.text)
        span = _find_active_label_span(lines)
        if span is None:
            continue

        start, end, tail = span
        if tail or start != 0 or end != len(lines):
            continue

        right_blocks = [
            block
            for block in blocks
            if block is not label
            and block.x0 > label.x1 + 20
            and _vertical_overlap(label, block) >= 0.35
        ]
        if not right_blocks:
            continue

        for value_block in sorted(right_blocks, key=lambda block: block.x0):
            if _candidate_belongs_to_nearby_field(value_block, label, blocks):
                continue

            value_lines = _merge_wrapped_name_lines(
                semantic_lines(value_block.text)
            )
            if not value_lines:
                continue
            if any(
                re.match(r"(?i)^\s*[a-z]\.\s+", line)
                for line in value_lines
            ):
                continue
            if any(_extract_concentration(line) for line in value_lines):
                continue
            if not all(_looks_like_name(line) for line in value_lines):
                continue

            names = [clean_visible_text(line) for line in value_lines]
            context = " | ".join(
                [clean_visible_text(label.text), clean_visible_text(value_block.text)]
            )
            return [
                ActiveIngredientEvidence(
                    name=name,
                    source_file=source_file,
                    page=page_number,
                    concentration="",
                    cas="",
                    context=context,
                )
                for name in names
            ]

    return []


_ENUMERATED_COMMON_NAME = re.compile(
    r"(?i)^\s*([a-z])\.\s+"
    r"([A-Za-zÁÉÍÓÚÜÑáéíóúüñ][A-Za-zÁÉÍÓÚÜÑáéíóúüñ .'-]{1,100})\s*$"
)
_ENUMERATED_CAS = re.compile(
    r"(?i)^\s*([a-z])\.\s+(\d{2,7}\s*-\s*\d{2}\s*-\s*\d)\s*$"
)


def _nearby_right_blocks(
    label: PdfTextBlock,
    blocks: list[PdfTextBlock],
    *,
    vertical_margin: float = 26,
) -> list[PdfTextBlock]:
    """Return value cells rendered to the right of a compact table label."""
    return [
        block
        for block in blocks
        if block is not label
        and block.x0 > label.x1 + 20
        and block.y0 <= label.y1 + vertical_margin
        and block.y1 >= label.y0 - vertical_margin
    ]


def _extract_enumerated_active_table_identity(
    blocks: list[PdfTextBlock],
    source_file: str,
    page_number: int,
) -> list[ActiveIngredientEvidence]:
    """Recover a/b active-ingredient tables whose labels occupy the left column.

    Some technical sheets center the left label vertically while the values
    appear as separate right-column blocks, for example:
        Ingrediente Activo | a. Substance A / b. Substance B
        No CAS Ingrediente Activo | a. 123-45-6 / b. 789-01-2
        Concentración | a. 100 g/kg / b. 300 g/kg

    Pair values only when the document explicitly provides these table labels;
    this prevents unrelated enumerated prose from becoming product identity.
    """
    active_label = next(
        (
            block
            for block in blocks
            if match_key(block.text) in {"ingrediente activo", "ingredientes activos"}
        ),
        None,
    )
    if active_label is None:
        return []

    cas_label = next(
        (
            block
            for block in blocks
            if "cas ingrediente activo" in match_key(block.text)
        ),
        None,
    )
    concentration_label = next(
        (
            block
            for block in blocks
            if match_key(block.text).startswith("concentracion")
        ),
        None,
    )

    names: dict[str, tuple[str, PdfTextBlock]] = {}
    for block in _nearby_right_blocks(active_label, blocks):
        value = clean_visible_text(block.text)
        match = _ENUMERATED_COMMON_NAME.fullmatch(value)
        if not match:
            continue
        name = match.group(2).strip(" :-/|;,.")
        if not _looks_like_name(name):
            continue
        names[match.group(1).lower()] = (name, block)

    if not names:
        return []

    cas_by_key: dict[str, str] = {}
    if cas_label is not None:
        for block in _nearby_right_blocks(cas_label, blocks):
            match = _ENUMERATED_CAS.fullmatch(clean_visible_text(block.text))
            if not match:
                continue
            cas = normalize_text(match.group(2)).replace(" ", "")
            if is_valid_cas(cas):
                cas_by_key[match.group(1).lower()] = cas

    concentration_by_key: dict[str, str] = {}
    if concentration_label is not None:
        for block in _nearby_right_blocks(concentration_label, blocks):
            value = clean_visible_text(block.text)
            enumeration = re.match(r"(?i)^\s*([a-z])\.\s+(.+)$", value)
            if not enumeration:
                continue
            concentration = _extract_concentration(enumeration.group(2))
            if concentration:
                concentration_by_key[enumeration.group(1).lower()] = concentration

    context_blocks = [active_label]
    if cas_label is not None:
        context_blocks.append(cas_label)
    if concentration_label is not None:
        context_blocks.append(concentration_label)
    context = " | ".join(clean_visible_text(block.text) for block in context_blocks)

    return [
        ActiveIngredientEvidence(
            name=name,
            source_file=source_file,
            page=page_number,
            concentration=concentration_by_key.get(key, ""),
            cas=cas_by_key.get(key, ""),
            context=context,
        )
        for key, (name, _) in sorted(names.items())
    ]


def _extract_explicit_active_table_identity(
    blocks: list[PdfTextBlock],
    source_file: str,
    page_number: int,
) -> list[ActiveIngredientEvidence]:
    """Recover a row from an explicitly labelled active-ingredient table.

    Some SDS PDFs extract each table column as a separate block and in a
    non-row order. The header itself still says INGREDIENTE ACTIVO and names
    identity/percentage columns, so pair the nearest row cells geometrically
    instead of reading subsequent prose as identities.
    """
    for header in blocks:
        header_key = match_key(header.text)
        if not has_active_marker(header.text):
            continue
        if not any(
            cue in header_key
            for cue in (
                "identificador del producto",
                "porcentaje",
                "concentracion",
                "cas",
            )
        ):
            continue

        row_blocks = [
            block
            for block in blocks
            if block is not header
            and block.y0 >= header.y1 - 2
            and block.y0 <= header.y1 + 150
        ]
        name_candidates = []
        for block in row_blocks:
            text = clean_visible_text(block.text)
            if not text or _starts_structural_field(semantic_lines(block.text)):
                continue

            cas_values = extract_valid_cas(text)
            compact = _compact_common_name(_strip_concentration(text))
            if not compact:
                continue
            if not cas_values and block.x0 > header.x0 + (header.x1 - header.x0) * 0.55:
                continue
            name_candidates.append((block, compact, cas_values))

        if not name_candidates:
            continue

        # The first data row is the block nearest the table header.
        name_block, name, own_cas = min(
            name_candidates,
            key=lambda item: (abs(item[0].y0 - header.y1), item[0].x0),
        )

        cas = own_cas[0] if len(own_cas) == 1 else ""
        if not cas:
            nearby_cas = []
            for block in row_blocks:
                if abs(block.y0 - name_block.y0) > 35:
                    continue
                nearby_cas.extend(extract_valid_cas(block.text))
            unique_cas = list(dict.fromkeys(nearby_cas))
            if len(unique_cas) == 1:
                cas = unique_cas[0]

        concentration = ""
        concentration_blocks = []
        for block in row_blocks:
            value = _extract_concentration(block.text)
            if not value:
                continue
            concentration_blocks.append((abs(block.y0 - name_block.y0), value))
        if concentration_blocks:
            concentration = min(concentration_blocks, key=lambda item: item[0])[1]

        context = " | ".join(
            clean_visible_text(block.text)
            for block in [header, *row_blocks]
            if clean_visible_text(block.text)
        )
        return [
            ActiveIngredientEvidence(
                name=name,
                source_file=source_file,
                page=page_number,
                concentration=concentration,
                cas=cas,
                context=context,
            )
        ]

    return []


def _extract_composition_row_fallback(
    text: str,
    source_file: str,
    page_number: int,
) -> list[ActiveIngredientEvidence]:
    """Recover concentration-bearing composition rows from spatial text.

    Some table PDFs merge the active-ingredient header with a neighbouring
    properties panel. Their block geometry can therefore be ambiguous even
    though the sorted page text still preserves a row such as
    "Ácido 1-naftalenacético (ANA) 60 g/kg". This fallback only accepts rows
    with an explicit concentration immediately following the candidate name.
    """
    lines = semantic_lines(text)
    evidence: list[ActiveIngredientEvidence] = []

    for index, line in enumerate(lines):
        # This fallback is only for an actual field-style active-ingredient
        # label. Narrative mentions such as "El ingrediente activo Malathion
        # es..." must not license nearby ecotoxicology values as identities.
        if _active_label_span_at(lines, index) is None:
            continue

        for row in lines[index + 1 : index + 8]:
            if _is_stop(row) or _starts_structural_field([row]):
                break
            concentration_match = _CONCENTRATION.search(row)
            if not concentration_match:
                continue

            raw_name = row[: concentration_match.start()].strip(" :-/|;,.+")
            raw_name = re.sub(r"(?i)^aspecto?\s*:\s*", "", raw_name).strip()
            if not _looks_like_name(raw_name):
                continue

            cas_values = extract_valid_cas(row)
            evidence.append(
                ActiveIngredientEvidence(
                    name=clean_visible_text(raw_name),
                    source_file=source_file,
                    page=page_number,
                    concentration=concentration_match.group(1).strip(),
                    cas=cas_values[0] if len(cas_values) == 1 else "",
                    context=" | ".join(
                        lines[max(0, index - 2) : min(len(lines), index + 8)]
                    ),
                )
            )
            break

        if evidence:
            break

    return evidence


def _extract_single_component_sds_identity(
    document: PdfDocument,
) -> list[ActiveIngredientEvidence]:
    """Recognize a pure/single-component SDS as product chemical identity.

    A 100% composition row is decisive chemical identity even when the SDS does
    not literally say "ingrediente activo". The CAS may be on the same line or
    in an adjacent table cell/line; if section 1 also exposes a CAS, both must
    agree.
    """
    if not document.pages:
        return []

    identifier_text = " ".join((page.text or "") for page in document.pages[:2])
    identifier_key = match_key(identifier_text)
    if not (
        "identificador del producto" in identifier_key
        or "product identifier" in identifier_key
        or "product name" in identifier_key
        or "nombre comercial" in identifier_key
    ):
        return []

    identifier_cas = set(extract_valid_cas(identifier_text))
    hundred = re.compile(
        r"(?i)(?P<full>(?:<=|≤|<)?\s*100(?:[.,]0+)?\s*%)"
    )

    # Prefer an explicit product-name identity when the same name reappears in
    # the 100% composition section and the CAS is consistent. This is safer
    # than deriving a name from whatever text happens to precede the
    # concentration cell in a visually complex SDS table.
    product_names: list[str] = []
    identifier_lines = semantic_lines(identifier_text)
    for index, line in enumerate(identifier_lines):
        cleaned = clean_visible_text(line)
        inline = re.match(
            r"(?i)^\s*(?:product\s+name|nombre\s+del\s+producto|"
            r"nombre\s+comercial)\s*:?[ \t]*(.+?)\s*$",
            cleaned,
        )
        if inline and inline.group(1).strip(" :"):
            value = inline.group(1).strip(" :-/|;,.")
            if _looks_like_name(value):
                product_names.append(value)
                continue

        key = match_key(cleaned)
        if key not in {"product name", "nombre del producto", "nombre comercial"}:
            continue
        for candidate in identifier_lines[index + 1 : index + 4]:
            value = candidate.strip(" :-/|;,.")
            if not value or value == ":":
                continue
            if _looks_like_name(value):
                product_names.append(value)
            break

    product_names = list(dict.fromkeys(product_names))

    for page in document.pages:
        text = page.text or ""
        if not has_composition_marker(text):
            continue

        lines = semantic_lines(text)
        page_hundred = hundred.search(clean_visible_text(text))
        if page_hundred and product_names:
            page_key = f" {match_key(text)} "
            page_cas = set(extract_valid_cas(text))
            consistent_cas = (
                sorted(identifier_cas & page_cas)
                if identifier_cas and page_cas
                else sorted(identifier_cas or page_cas)
            )
            for product_name in product_names:
                name_key = match_key(product_name)
                if not name_key or f" {name_key} " not in page_key:
                    continue
                if identifier_cas and page_cas and not consistent_cas:
                    continue
                cas = consistent_cas[0] if len(consistent_cas) == 1 else ""
                return [
                    ActiveIngredientEvidence(
                        name=clean_visible_text(product_name),
                        source_file=document.file_name,
                        page=page.page,
                        concentration=page_hundred.group("full").strip(),
                        cas=cas,
                        context=" | ".join(lines[:12]),
                    )
                ]

        for index, line in enumerate(lines):
            concentration_match = hundred.search(line)
            if not concentration_match:
                continue

            raw_name = line[: concentration_match.start()].strip()
            raw_name = CAS_PATTERN.sub(" ", raw_name)
            raw_name = re.sub(
                r"(?i)\b(?:n[uú]mero\s+)?cas\b\s*[:#-]?",
                " ",
                raw_name,
            )
            name = re.sub(r"\s+", " ", raw_name).strip(" :-/|;,.+")
            if not _looks_like_name(name):
                compact = _compact_common_name(name)
                if compact:
                    name = compact
            if not _looks_like_name(name):
                continue

            window = " | ".join(
                lines[max(0, index - 8) : min(len(lines), index + 4)]
            )
            cas_values = extract_valid_cas(window)
            if len(cas_values) != 1:
                continue
            cas = cas_values[0]
            if identifier_cas and cas not in identifier_cas:
                continue

            return [
                ActiveIngredientEvidence(
                    name=clean_visible_text(name),
                    source_file=document.file_name,
                    page=page.page,
                    concentration=concentration_match.group("full").strip(),
                    cas=cas,
                    context=window,
                )
            ]

    return []


def _extract_from_lines(
    text: str,
    source_file: str,
    page_number: int,
) -> list[ActiveIngredientEvidence]:
    """Fallback for synthetic fixtures or PDFs without block metadata."""
    lines = semantic_lines(text)
    evidence: list[ActiveIngredientEvidence] = []

    marker_index = 0
    while marker_index < len(lines):
        span = _active_label_span_at(lines, marker_index)
        if span is None:
            marker_index += 1
            continue

        end_index, tail = span
        payload: list[str] = [tail] if tail else []
        metadata_lines: list[str] = []

        window = lines[end_index : end_index + 8]
        cursor = 0
        while cursor < len(window):
            candidate = window[cursor]
            if _is_stop(candidate) or _active_label_tail(candidate) is not None:
                break

            if _starts_structural_field([candidate]):
                concentration, cas = _metadata_values([candidate])
                if concentration or cas:
                    metadata_lines.append(candidate)
                    cursor += 1
                    continue

                # PDF/plain-text extraction can split a metadata label from
                # its value, e.g. "Concentración:" then "480 g/L". Consume
                # only narrowly chemical metadata fields; do not walk through
                # fields such as "Nombre químico" and accidentally absorb
                # systematic-name prose as active identity.
                key = match_key(candidate)
                metadata_field = any(
                    key == prefix or key.startswith(prefix + " ")
                    for prefix in (
                        "concentracion",
                        "contenido",
                        "cas",
                        "numero cas",
                        "n cas",
                    )
                )
                if metadata_field and cursor + 1 < len(window):
                    next_candidate = window[cursor + 1]
                    if (
                        not _is_stop(next_candidate)
                        and _active_label_tail(next_candidate) is None
                        and not _starts_structural_field([next_candidate])
                    ):
                        next_concentration, next_cas = _metadata_values(
                            [next_candidate]
                        )
                        if next_concentration or next_cas:
                            metadata_lines.extend([candidate, next_candidate])
                            cursor += 2
                            continue
                break

            payload.append(candidate)
            cursor += 1

        context = " | ".join(
            lines[max(0, marker_index - 2) : min(len(lines), marker_index + 8)]
        )
        candidates = _candidate_tuples(
            payload,
            metadata_text=" | ".join(metadata_lines),
        )

        # Product headers are often repeated above recommendation tables. In a
        # plain-text extraction, the singular "INGREDIENTE ACTIVO: GLIFOSATO"
        # can then be followed by biological targets and an application dose,
        # making weeds look like additional active ingredients. When the label
        # is singular and the nearby text clearly belongs to a use/dose table,
        # keep only the first unambiguous identity from that header.
        label_key = match_key(" ".join(lines[marker_index:end_index]))
        lookahead = lines[end_index : end_index + 20]
        lookahead_key = match_key(" ".join(lookahead))
        use_table_context = (
            "ingredientes activos" not in label_key
            and "active ingredients" not in label_key
            and any(
                cue in lookahead_key
                for cue in (
                    "recomendaciones de uso",
                    "objetivo biologico",
                    "dosis",
                )
            )
            and any(_APPLICATION_RATE.search(line) for line in lookahead)
        )
        if (
            use_table_context
            and len(candidates) > 1
            and all(not concentration for _, concentration, _ in candidates)
        ):
            candidates = candidates[:1]

        evidence.extend(
            _evidence_from_candidates(
                candidates,
                source_file=source_file,
                page_number=page_number,
                context=context,
            )
        )
        marker_index = end_index

    return evidence


def _enrich_active_concentrations_from_document(
    evidence: list[ActiveIngredientEvidence],
    document: PdfDocument,
) -> None:
    """Fill a missing concentration from an exact named concentration field.

    Some SDS files identify the active ingredient and CAS in section 2/3, but
    place the formulation concentration later under physical/chemical
    properties, e.g. "Concentración: 100 g/l Novaluron." This enrichment never
    creates identity; it only fills metadata for an already confirmed active
    name and requires that same normalized name on the concentration line.
    """
    for item in evidence:
        if item.concentration:
            continue

        name_key = match_key(item.name)
        if not name_key:
            continue

        for page in document.pages:
            for line in semantic_lines(page.text or ""):
                line_key = match_key(line)
                if not line_key.startswith("concentracion"):
                    continue
                if f" {name_key} " not in f" {line_key} ":
                    continue
                concentration = _extract_concentration(line)
                if not concentration:
                    continue
                item.concentration = concentration
                break
            if item.concentration:
                break

        if item.concentration or not item.cas:
            continue

        # Conservative Section 3 fallback for split-column SDS tables. If the
        # same confirmed active name and CAS occur on a composition page and
        # that page exposes exactly one concentration-like value, use it only
        # as metadata enrichment. This never creates a new active identity.
        for page in document.pages:
            text = page.text or ""
            if not has_composition_marker(text):
                continue
            page_key = match_key(text)
            if f" {name_key} " not in f" {page_key} ":
                continue
            if item.cas not in extract_valid_cas(text):
                continue

            concentrations: list[str] = []
            for line in semantic_lines(text):
                value = _extract_concentration(line)
                if value and value not in concentrations:
                    concentrations.append(value)
            if len(concentrations) == 1:
                item.concentration = concentrations[0]
                break


def extract_active_ingredients(document: PdfDocument) -> list[ActiveIngredientEvidence]:
    """Extract explicitly labelled active ingredients independently of list matches."""
    evidence: list[ActiveIngredientEvidence] = []

    for page in document.pages:
        if page.blocks:
            page_evidence = _extract_right_column_active_identity(
                page.blocks,
                document.file_name,
                page.page,
            )
            if not page_evidence:
                page_evidence = _extract_from_blocks(
                    page.blocks,
                    document.file_name,
                    page.page,
                )
            if not page_evidence:
                page_evidence = _extract_enumerated_active_table_identity(
                    page.blocks,
                    document.file_name,
                    page.page,
                )
            if not page_evidence:
                page_evidence = _extract_explicit_active_table_identity(
                    page.blocks,
                    document.file_name,
                    page.page,
                )
        else:
            page_evidence = _extract_from_lines(
                page.text or "",
                document.file_name,
                page.page,
            )

        narrative_evidence = _extract_narrative_active_identity(
            page.text or "",
            document.file_name,
            page.page,
        )

        # Prefer an explicit declarative active-ingredient sentence over the
        # generic concentration-row fallback. The latter is intended for
        # ambiguous composition tables and must not reinterpret a wrapped
        # narrative fragment such as "potasio en una concentración de 443 g/L"
        # as a second active ingredient.
        if not narrative_evidence and not page_evidence:
            row_fallback = _extract_composition_row_fallback(
                page.text or "",
                document.file_name,
                page.page,
            )
            if row_fallback:
                page_evidence = row_fallback

        evidence.extend(page_evidence)

        evidence.extend(
            _extract_iupac_ia_identity(
                page.text or "",
                document.file_name,
                page.page,
            )
        )
        evidence.extend(
            _extract_other_identifier_identity(
                page.text or "",
                document.file_name,
                page.page,
            )
        )

        # Some FT files declare the active ingredient in a direct sentence
        # rather than a field/table. This path is deliberately narrow and only
        # accepts explicit declarative phrasing.
        evidence.extend(narrative_evidence)

    # Some SDS documents establish the pesticide identity by correlating
    # section 1 ("Otros medios de identificación") with a later concentration
    # field rather than by using the literal label "Ingrediente activo".
    evidence.extend(_extract_correlated_sds_identifier_identity(document))

    if not evidence:
        evidence.extend(_extract_single_component_sds_identity(document))

    _enrich_active_concentrations_from_document(evidence, document)

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
