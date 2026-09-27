"""Presentation-only interpretation of criteria recorded in the local pesticide lists.

This module does not classify chemicals or change evaluation rules. It only renders
class and category context that is explicitly present in the normalized source data.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata


@dataclass(frozen=True)
class CriterionExplanation:
    label: str
    explanation: str
    system: str | None = None
    hazard_class: str | None = None
    category: str | None = None
    ra_hhp_criterion: bool = False


def _fold(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    return "".join(char for char in normalized if not unicodedata.combining(char))


def _split_items(criteria: str | None) -> list[str]:
    return [item.strip() for item in (criteria or "").split(";") if item.strip()]


_CMR_CLASSES = {
    "carcinogenicidad": "Carcinogenicidad",
    "carcinogenicity": "Carcinogenicidad",
    "mutagenicidad": "Mutagenicidad",
    "mutagenicity": "Mutagenicidad",
    "germ cell mutagenicity": "Mutagenicidad",
    "mutagenicity of germ cells": "Mutagenicidad",
    "toxicidad reproductiva": "Toxicidad reproductiva",
    "toxicidad para la reproduccion": "Toxicidad reproductiva",
    "reproductive toxicity": "Toxicidad reproductiva",
}
_GHS_CATEGORY = re.compile(r"\b(?:GHS|SGA)\s*(?:categor[ií]a\s*)?([1-4][AB]?)\b", re.I)
_WHO_CLASS = re.compile(r"\b(?:OMS|WHO)\s*(?:class(?:e)?\s*)?(IA|IB|II|III|U|1A|1B|2|3)\b", re.I)
_ACUTE_CATEGORY = re.compile(r"\b(IA|IB|II|III|U|1A|1B|2|3)\b", re.I)

_WHO_CATEGORIES = {
    "1A": ("Ia", "extremadamente peligroso"),
    "IA": ("Ia", "extremadamente peligroso"),
    "1B": ("Ib", "altamente peligroso"),
    "IB": ("Ib", "altamente peligroso"),
    "2": ("II", "moderadamente peligroso"),
    "II": ("II", "moderadamente peligroso"),
    "3": ("III", "ligeramente peligroso"),
    "III": ("III", "ligeramente peligroso"),
    "U": ("U", "poco probable que presente peligro agudo bajo uso normal"),
}

_GHS_CMR_MEANINGS = {
    ("Carcinogenicidad", "1A"): "Se sabe que causa cáncer en seres humanos.",
    ("Carcinogenicidad", "1B"): "Se presume que causa cáncer en seres humanos.",
    ("Carcinogenicidad", "2"): "Se sospecha que puede causar cáncer.",
    ("Mutagenicidad", "1A"): "Se sabe que induce mutaciones hereditarias en células germinales humanas.",
    ("Mutagenicidad", "1B"): "Se presume que induce mutaciones hereditarias en células germinales humanas.",
    ("Mutagenicidad", "2"): "Se sospecha que puede inducir mutaciones hereditarias en células germinales humanas.",
    ("Toxicidad reproductiva", "1A"): "Se sabe que es tóxico para la reproducción humana.",
    ("Toxicidad reproductiva", "1B"): "Se presume que es tóxico para la reproducción humana.",
    ("Toxicidad reproductiva", "2"): "Se sospecha que puede ser tóxico para la reproducción humana.",
}

_CONVENTIONS = {
    "M": (
        "Protocolo de Montreal",
        "Controla y elimina gradualmente sustancias que agotan la capa de ozono.",
    ),
    "R": (
        "Convenio de Rotterdam",
        "Aplica el procedimiento de consentimiento fundamentado previo a ciertos químicos y plaguicidas en el comercio internacional; no es por sí solo una prohibición general.",
    ),
    "E": (
        "Convenio de Estocolmo",
        "Busca proteger la salud y el ambiente frente a contaminantes orgánicos persistentes; las medidas dependen del anexo aplicable.",
    ),
}

_MITIGATION = {
    "epp": ("Protección personal de nivel superior (EPP)", "EPP"),
    "riesgo acuatico": ("Riesgo para organismos acuáticos", "Riesgo acuático"),
    "vida silvestre": ("Riesgo para la vida silvestre", "Vida silvestre"),
    "polinizadores": ("Riesgo para polinizadores", "Polinizadores"),
    "espectador": ("Riesgo de exposición para personas presentes en las inmediaciones", "Espectador"),
}


def _criterion_class(label: str) -> str | None:
    folded = _fold(label)
    for alias, display in _CMR_CLASSES.items():
        if alias in folded:
            return display
    return None


def _explain_ghs(item: str, source_list: str) -> CriterionExplanation | None:
    match = _GHS_CATEGORY.search(item)
    if not match:
        return None

    category = match.group(1).upper()
    before_category = item[:match.start()]
    # The class is taken from the text before the GHS category, commonly
    # "Carcinogenicidad: GHS 1B". A bare "GHS 1B" deliberately has no class.
    label_part = re.sub(r"\b(?:GHS|SGA)\b", "", before_category, flags=re.I)
    label_part = label_part.strip(" :-·|")
    hazard_class = _criterion_class(label_part)

    if hazard_class:
        label = f"{hazard_class} · GHS {category}"
        meaning = _GHS_CMR_MEANINGS.get((hazard_class, category))
        relevant = source_list == "PROHIBITED" and category in {"1A", "1B"}
        if meaning and relevant:
            explanation = (
                f"{meaning} Esta clase y categoría forman parte de los criterios "
                "SGA de Rainforest Alliance para plaguicidas altamente peligrosos."
            )
        elif meaning:
            explanation = (
                f"{meaning} La categoría se interpreta dentro de esta clase; "
                "el registro no la identifica como criterio SGA 1A/1B de Rainforest Alliance."
            )
        else:
            explanation = (
                f"La fuente registra GHS {category} para {hazard_class.lower()}. "
                "La categoría debe interpretarse dentro de esta clase de peligro."
            )
        return CriterionExplanation(
            label, explanation, "GHS/SGA", hazard_class, category, relevant
        )

    # Preserve an explicitly named non-CMR class, but do not map it to an RA
    # carcinogenicity, mutagenicity, or reproductive-toxicity criterion.
    if label_part:
        label = f"{label_part} · GHS {category}"
        explanation = (
            f"La fuente registra GHS {category} para esta clase. La categoría "
            "no se interpreta como carcinogenicidad, mutagenicidad ni toxicidad "
            "reproductiva."
        )
        return CriterionExplanation(label, explanation, "GHS/SGA", label_part, category, False)

    return CriterionExplanation(
        f"GHS {category} · clase de peligro no indicada",
        "La fuente no identifica la clase de peligro. No es posible determinar "
        "el significado toxicológico ni si corresponde a un criterio SGA de "
        "Rainforest Alliance; la aplicación no infiere esa clase.",
        "GHS/SGA",
        None,
        category,
        False,
    )


def _explain_who(item: str, source_list: str) -> CriterionExplanation | None:
    if _GHS_CATEGORY.search(item):
        return None
    label, separator, value = item.partition(":")
    folded_label = _fold(label)
    match = _WHO_CLASS.search(item)
    category = match.group(1).upper() if match else None

    # The local RA list stores this system as "Toxicidad aguda: 1A/1B".
    # Only that explicit hazard-class label permits interpreting a bare level
    # as the WHO pesticide acute-hazard class.
    if not category and "toxicidad aguda" in folded_label:
        level = _ACUTE_CATEGORY.search(value if separator else "")
        category = level.group(1).upper() if level else None
    if not category:
        return None

    who_category, meaning = _WHO_CATEGORIES[category]
    relevant = source_list == "PROHIBITED" and who_category in {"Ia", "Ib"}
    label_text = f"Toxicidad aguda · OMS {who_category}"
    if relevant:
        explanation = (
            f"La OMS clasifica el plaguicida como {meaning} por toxicidad aguda. "
            "Las clases OMS Ia e Ib forman parte de los criterios de alta peligrosidad "
            "utilizados por Rainforest Alliance."
        )
    else:
        explanation = (
            f"La clasificación OMS indica que es {meaning} por toxicidad aguda. "
            "Esta categoría no corresponde al criterio OMS Ia/Ib de Rainforest Alliance."
        )
    return CriterionExplanation(
        label_text, explanation, "OMS", "Toxicidad aguda", who_category, relevant
    )


def _explain_ra_marker(item: str, source_list: str) -> CriterionExplanation | None:
    label, separator, value = item.partition(":")
    if not separator:
        return None
    hazard_class = _criterion_class(label)
    if not hazard_class or value.strip() not in {"✓", "✔", "SI", "Sí", "X", "x"}:
        return None
    if source_list != "PROHIBITED":
        return None

    return CriterionExplanation(
        f"{hazard_class} · GHS 1A/1B",
        "La lista de Rainforest Alliance marca esta clase de peligro dentro de los "
        "criterios SGA 1A/1B. La fila local identifica la clase, pero no especifica "
        "si la subcategoría es 1A o 1B.",
        "GHS/SGA",
        hazard_class,
        "1A/1B",
        True,
    )


def _explain_convention(item: str) -> list[CriterionExplanation]:
    label, separator, value = item.partition(":")
    if not separator or "convenciones internacionales" not in _fold(label):
        return []
    codes = re.findall(r"(?<![A-Z])([MRE])(?![A-Z])", value.upper())
    return [
        CriterionExplanation(f"Referencia a { _CONVENTIONS[code][0] }", _CONVENTIONS[code][1], "Convenio")
        for code in dict.fromkeys(codes)
    ]


def _explain_mitigation(item: str) -> CriterionExplanation | None:
    folded = _fold(item.strip())
    for key, (display, source_label) in _MITIGATION.items():
        if folded == key:
            return CriterionExplanation(display, f"La lista de mitigación identifica: {source_label}.", "Rainforest Alliance")
    return None


def interpret_criterion(item: str, source_list: str = "PROHIBITED") -> CriterionExplanation:
    """Return a human-readable interpretation without filling missing context."""
    ghs = _explain_ghs(item, source_list)
    if ghs:
        return ghs

    who = _explain_who(item, source_list)
    if who:
        return who

    ra_marker = _explain_ra_marker(item, source_list)
    if ra_marker:
        return ra_marker

    conventions = _explain_convention(item)
    if conventions:
        return conventions[0]

    mitigation = _explain_mitigation(item)
    if mitigation:
        return mitigation

    return CriterionExplanation(
        item.strip() or "Criterio de la lista",
        "La lista registra este criterio; la información disponible no permite añadir una interpretación más específica.",
        source_list or None,
    )


def interpret_criteria(criteria: str | None, source_list: str = "PROHIBITED") -> list[CriterionExplanation]:
    """Interpret each semicolon-separated criterion from the normalized list."""
    results: list[CriterionExplanation] = []
    for item in _split_items(criteria):
        if source_list == "MITIGATE_RISK":
            mapped = _explain_mitigation(item)
            if mapped:
                results.append(mapped)
                continue

        if "convenciones internacionales" in _fold(item):
            _, _, value = item.partition(":")
            codes = re.findall(r"(?<![A-Z])([MRE])(?![A-Z])", value.upper())
            if codes:
                results.extend(
                    CriterionExplanation(
                        f"Referencia a {_CONVENTIONS[code][0]}",
                        _CONVENTIONS[code][1],
                        "Convenio",
                    )
                    for code in dict.fromkeys(codes)
                )
                continue

        results.append(interpret_criterion(item, source_list))
    return results
