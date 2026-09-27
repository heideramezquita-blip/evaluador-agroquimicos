"""Presentation helpers for consolidating duplicate evidence cards."""

from __future__ import annotations

import unicodedata


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
                "contexts": [],
                "hit_items": [],
                "_criterion_values": [],
                "_usage_values": [],
                "_version_values": [],
            },
        )
        if hit.page:
            group["pages"].add(hit.page)
        group["classes"].add(hit.context_class)
        if hit.context and hit.context not in group["contexts"]:
            group["contexts"].append(hit.context)
        group["hit_items"].append(hit)
        for field, value in (
            ("_criterion_values", entry.criteria),
            ("_usage_values", entry.usage),
            ("_version_values", entry.source_version),
        ):
            if value and _normalized_text(value) not in {
                _normalized_text(item) for item in group[field]
            }:
                group[field].append(value.strip())

    results = []
    for group in grouped.values():
        if group["_criterion_values"]:
            group["criteria"] = "; ".join(group["_criterion_values"])
        if group["_usage_values"]:
            group["usage"] = ", ".join(group["_usage_values"])
        if group["_version_values"]:
            group["source_version"] = "; ".join(group["_version_values"])
        for internal in ("_criterion_values", "_usage_values", "_version_values"):
            del group[internal]
        results.append(group)
    return results
