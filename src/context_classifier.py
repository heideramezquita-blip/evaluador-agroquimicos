from __future__ import annotations

import re

from .text_utils import normalize_text

ACTIVE = "ACTIVE"
COMPOSITION = "COMPOSITION"
INCIDENTAL = "INCIDENTAL"
NEGATED = "NEGATED"
DECOMPOSITION = "DECOMPOSITION_COMBUSTION"
REFERENCE = "REFERENCE_TOXICOLOGY"
UNCERTAIN = "UNCERTAIN"

_COMPOSITION_HEADING = re.compile(
    r"\bcomposicion\s*/?\s*informacion\s+sobre\s+los\s+(?:ingredientes|componentes)\b"
)

_ACTIVE_MARKERS = (
    "ingrediente activo",
    "ingredientes activos",
    "principio activo",
    "principios activos",
    "active ingredient",
    "active ingredients",
)


def _has_composition_heading(normalized: str) -> bool:
    return (
        "composicion garantizada" in normalized
        or bool(_COMPOSITION_HEADING.search(normalized))
    )


def has_identity_marker(text: str) -> bool:
    """Return whether text explicitly exposes product chemical identity.

    Formatting around slashes in SDS section headings varies between PDF
    producers and text extractors (e.g. "COMPOSICIÓN /INFORMACIÓN",
    "COMPOSICIÓN/ INFORMACIÓN", or no slash). Treat those variants as the
    same composition heading instead of relying on one literal string.
    """
    normalized = normalize_text(text)
    return any(marker in normalized for marker in _ACTIVE_MARKERS) or _has_composition_heading(normalized)


def classify_context(context: str, matched_value: str = "") -> str:
    n = normalize_text(context)

    if any(x in n for x in ("no contiene", "no contiene el", "does not contain", "libre de ")):
        return NEGATED
    if any(
        x in n
        for x in (
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
    ):
        return DECOMPOSITION
    if any(
        x in n
        for x in (
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
    ):
        return REFERENCE
    if any(
        x in n
        for x in (
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
    ):
        return INCIDENTAL
    if any(marker in n for marker in _ACTIVE_MARKERS):
        return ACTIVE
    if _has_composition_heading(n):
        return COMPOSITION
    return UNCERTAIN
