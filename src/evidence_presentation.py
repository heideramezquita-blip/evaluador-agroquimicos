"""Presentation helpers for evidence cards and technical traceability."""

from __future__ import annotations

import unicodedata

from .context_classifier import (
    ACTIVE,
    COMPOSITION,
    PRODUCT_IDENTITY,
    DECOMPOSITION,
    INCIDENTAL,
    NEGATED,
    REFERENCE,
    REFERENCE_LIST,
    UNCERTAIN,
)


LIST_LABELS = {
    "PROHIBITED": "RA · Prohibidos",
    "OBSOLETE": "RA · Obsoletos",
    "MITIGATE_RISK": "RA · Mitigación de riesgos",
}

CONTEXT_LABELS = {
    ACTIVE: "Ingrediente activo",
    COMPOSITION: "Composición del producto",
    PRODUCT_IDENTITY: "Identidad del producto",
    INCIDENTAL: "Mención incidental",
    NEGATED: "Mención negada",
    DECOMPOSITION: "Descomposición / combustión",
    REFERENCE: "Referencia toxicológica",
    REFERENCE_LIST: "Lista / referencia normativa",
    UNCERTAIN: "Papel en el producto por confirmar",
}

CONTEXT_PRIORITY = {
    ACTIVE: 0,
    COMPOSITION: 1,
    PRODUCT_IDENTITY: 2,
    UNCERTAIN: 3,
    INCIDENTAL: 4,
    NEGATED: 5,
    REFERENCE: 6,
    REFERENCE_LIST: 7,
    DECOMPOSITION: 8,
}

CHANNEL_LABELS = {"CAS": "CAS", "NAME": "Nombre", "GROUP_NAME": "Grupo"}

USAGE_LABELS = {
    "A": "Acaricida",
    "Ad": "Adyuvante",
    "Fun": "Fungicida",
    "Fum": "Fumigante",
    "H": "Herbicida",
    "I": "Insecticida",
    "N": "Nematicida",
    "R": "Rodenticida",
    "Conserv. Mad.": "Conservación de la madera",
}


def list_label(source_list: str) -> str:
    return LIST_LABELS.get(source_list, source_list)


def context_label(value: str) -> str:
    return CONTEXT_LABELS.get(value, value.replace("_", " ").title())


def channel_label(value: str) -> str:
    return CHANNEL_LABELS.get(value, value)


def usage_label(value: str | None) -> str:
    if not value:
        return ""
    return " · ".join(
        USAGE_LABELS.get(item.strip(), item.strip())
        for item in value.split(",")
        if item.strip()
    )


def evidence_pages(group: dict) -> str:
    ranked = [
        (CONTEXT_PRIORITY.get(hit.context_class, 9), hit.page)
        for hit in group.get("hit_items", [])
        if hit.page
    ]
    if not ranked:
        return "—"

    best_priority = min(priority for priority, _ in ranked)
    pages = sorted(
        {page for priority, page in ranked if priority == best_priority}
    )
    return ", ".join(map(str, pages))


def _normalized_text(value: str | None) -> str:
    text = unicodedata.normalize("NFKC", value or "")
    return " ".join(text.split()).casefold()


def _normalized_cas(value: str | None) -> str:
    text = unicodedata.normalize("NFKC", value or "").upper()
    return "".join(text.split()).replace("–", "-").replace("—", "-")


def consolidate_evidence_hits(hits):
    """Return one evidence-card record per list, substance, CAS and document.

    Detection can find the same entry by both its CAS and name. Values from
    imported list rows and filenames are normalized for the grouping key so
    invisible whitespace, casing, or Unicode differences do not create
    visually duplicate cards.
    """
    grouped = {}

    for hit in hits:
        entry = hit.entry
        key = (
            _normalized_text(entry.source_list),
            _normalized_text(entry.ingredient),
            _normalized_cas(entry.cas),
            _normalized_text(hit.source_file),
        )
        group = grouped.setdefault(
            key,
            {
                "ingredient": entry.ingredient.strip(),
                "cas": entry.cas or "Varios",
                "file": hit.source_file.strip(),
                "pages": set(),
                "classes": set(),
                "usage": entry.usage,
                "criteria": entry.criteria,
                "source_list": entry.source_list.strip(),
                "source_version": entry.source_version,
                "hit_items": [],
                "_criterion_values": [],
                "_usage_values": [],
                "_version_values": [],
            },
        )

        if hit.page:
            group["pages"].add(hit.page)
        group["classes"].add(hit.context_class)
        group["hit_items"].append(hit)

        for field, value in (
            ("_criterion_values", entry.criteria),
            ("_usage_values", entry.usage),
            ("_version_values", entry.source_version),
        ):
            normalized_values = {
                _normalized_text(item) for item in group[field]
            }
            if value and _normalized_text(value) not in normalized_values:
                group[field].append(value.strip())

    results = []
    for group in grouped.values():
        if group["_criterion_values"]:
            group["criteria"] = "; ".join(group["_criterion_values"])
        if group["_usage_values"]:
            group["usage"] = ", ".join(group["_usage_values"])
        if group["_version_values"]:
            group["source_version"] = "; ".join(group["_version_values"])

        for internal in (
            "_criterion_values",
            "_usage_values",
            "_version_values",
        ):
            del group[internal]
        results.append(group)

    return results
