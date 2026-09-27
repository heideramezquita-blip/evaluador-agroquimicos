from __future__ import annotations

import re

from .text_utils import match_key, normalize_text

ACTIVE = "ACTIVE"
COMPOSITION = "COMPOSITION"
INCIDENTAL = "INCIDENTAL"
NEGATED = "NEGATED"
DECOMPOSITION = "DECOMPOSITION_COMBUSTION"
REFERENCE = "REFERENCE_TOXICOLOGY"
UNCERTAIN = "UNCERTAIN"

_ACTIVE_PATTERNS = (
    re.compile(r"\bingrediente(?:s|\s+s)?\s+activo(?:s|\s+s)?\b"),
    re.compile(r"\bprincipio(?:s|\s+s)?\s+activo(?:s|\s+s)?\b"),
    re.compile(r"\bactive\s+ingredient(?:s|\s+s)?\b"),
)
_IA_MARKER = re.compile(
    r"(?:^|[^a-z0-9])i\s*\.?\s*a\s*\.?(?:$|[^a-z0-9])"
)

_NEGATED_MARKERS = (
    "no contiene",
    "no contiene el",
    "does not contain",
    "libre de ",
)
_DECOMPOSITION_MARKERS = (
    "productos de descomposicion",
    "producto de descomposicion",
    "productos de descoposicion",
    "producto de descoposicion",
    "descomposicion termica",
    "gases de combustion",
    "productos de combustion",
    "en caso de incendio",
    "gases desprendidos",
    "combustion",
    "incendio",
)
_REFERENCE_MARKERS = (
    "limite de exposicion",
    "limites de exposicion",
    "valor limite",
    "valores limite",
    "exposicion ocupacional",
    "informacion toxicologica",
    "toxicologia",
    "referencia bibliografica",
    "bibliografia",
)
_INCIDENTAL_MARKERS = (
    "incompatibilidad",
    "incompatibilidades",
    "no compatible",
    "incompatible",
    "precursor",
    "reaccion de condensacion",
    "condensacion con",
    "condensacion del",
    "obtenidos mediante la condensacion",
)


def has_active_marker(text: str) -> bool:
    """Return whether text contains an explicit active-ingredient label.

    PDF extractors frequently turn labels such as Ingrediente(s) Activo(s)
    into "ingrediente s activo s". Some pesticide SDS/FT documents also use
    the abbreviation I.A. next to chemical-identity labels. Accept those
    layout variants without treating arbitrary letters "IA" as proof.
    """
    normalized = normalize_text(text)
    if any(pattern.search(normalized) for pattern in _ACTIVE_PATTERNS):
        return True

    if _IA_MARKER.search(normalized) and any(
        cue in normalized
        for cue in (
            "iupac",
            "nombre quimico",
            "numero cas",
            "n cas",
            "cas",
            "ingrediente",
        )
    ):
        return True
    return False


def has_composition_marker(text: str) -> bool:
    """Recognize common FT/FDS composition-heading variants."""
    key = match_key(text)
    if not key:
        return False

    if any(
        marker in key
        for marker in (
            "composicion garantizada",
            "composicion porcentual",
            "analisis garantizado",
        )
    ):
        return True

    if re.search(
        r"\bcomposicion(?:\s+informacion)?(?:\s+(?:sobre|de))?"
        r"(?:\s+los)?\s+(?:ingredientes|componentes?)\b",
        key,
    ):
        return True

    if re.search(r"(?:^|\s)3\s+composicion(?:\s|$)", key):
        return True

    return False


def has_identity_marker(text: str) -> bool:
    """Return whether text explicitly exposes product chemical identity."""
    return has_active_marker(text) or has_composition_marker(text)


def _contains_any(normalized: str, markers: tuple[str, ...]) -> bool:
    return any(marker in normalized for marker in markers)


def _split_context(context: str) -> list[str]:
    return [
        part.strip()
        for part in re.split(r"\s*\|\s*|\n+", context or "")
        if part.strip()
    ]


def _nearest_distance(indices: list[int], matches: list[int]) -> int | None:
    if not indices or not matches:
        return None
    return min(abs(index - match) for index in indices for match in matches)


def _global_context_class(normalized: str) -> str:
    """Conservative fallback when a matched value cannot be localized."""
    if _contains_any(normalized, _NEGATED_MARKERS):
        return NEGATED
    if _contains_any(normalized, _DECOMPOSITION_MARKERS):
        return DECOMPOSITION
    if _contains_any(normalized, _REFERENCE_MARKERS):
        return REFERENCE
    if _contains_any(normalized, _INCIDENTAL_MARKERS):
        return INCIDENTAL
    if has_active_marker(normalized):
        return ACTIVE
    if has_composition_marker(normalized):
        return COMPOSITION
    return UNCERTAIN


def classify_context(context: str, matched_value: str = "") -> str:
    """Classify the role of a matched substance using local proximity.

    A wide context window can contain several section headings. For example,
    an FT may have an INFORMACIÓN TOXICOLÓGICA heading a few lines before
    "Ingrediente activo: Ametrina". Classifying the whole window by the first
    hazard word incorrectly turns explicit product identity into a toxicology
    reference. When the matched value can be located, prefer the marker nearest
    to that value and only let exclusion/reference signals dominate when they
    are genuinely local.
    """
    normalized = normalize_text(context)
    segments = _split_context(context)
    needle_key = match_key(matched_value)

    if not segments or not needle_key:
        return _global_context_class(normalized)

    segment_keys = [match_key(segment) for segment in segments]
    match_indices = [
        index
        for index, key in enumerate(segment_keys)
        if needle_key and f" {needle_key} " in f" {key} "
    ]
    if not match_indices:
        return _global_context_class(normalized)

    normalized_segments = [normalize_text(segment) for segment in segments]

    marker_indices = {
        NEGATED: [
            i
            for i, item in enumerate(normalized_segments)
            if _contains_any(item, _NEGATED_MARKERS)
        ],
        DECOMPOSITION: [
            i
            for i, item in enumerate(normalized_segments)
            if _contains_any(item, _DECOMPOSITION_MARKERS)
        ],
        REFERENCE: [
            i
            for i, item in enumerate(normalized_segments)
            if _contains_any(item, _REFERENCE_MARKERS)
        ],
        INCIDENTAL: [
            i
            for i, item in enumerate(normalized_segments)
            if _contains_any(item, _INCIDENTAL_MARKERS)
        ],
        ACTIVE: [
            i for i, item in enumerate(segments) if has_active_marker(item)
        ],
        COMPOSITION: [
            i for i, item in enumerate(segments) if has_composition_marker(item)
        ],
    }

    specs = (
        (NEGATED, 2, 0),
        (DECOMPOSITION, 2, 0),
        # An explicit active-ingredient label on the same semantic line is
        # stronger product-role evidence than a section heading that happens
        # to share that line after PDF layout reconstruction.
        (ACTIVE, 5, 1),
        (REFERENCE, 2, 2),
        (INCIDENTAL, 2, 2),
        (COMPOSITION, 12, 3),
    )
    candidates = []
    for category, max_distance, tie_priority in specs:
        distance = _nearest_distance(marker_indices[category], match_indices)
        if distance is not None and distance <= max_distance:
            candidates.append((distance, tie_priority, category))

    if candidates:
        return min(candidates)[2]

    return _global_context_class(normalized)
