from __future__ import annotations

from html import escape
from types import SimpleNamespace

from .cas_utils import is_valid_cas
from .criteria_presentation import interpret_criteria
from .rules import (
    STATUS_DOCUMENT_REVIEW,
    STATUS_IDENTITY_REVIEW,
    STATUS_MATCH_REVIEW,
    STATUS_MITIGATION,
    STATUS_MITIGATION_REVIEW,
    STATUS_NO_MATCH,
    STATUS_NO_USE,
    STATUS_NO_USE_RSPO,
    STATUS_OBSOLETE,
    STATUS_OBSOLETE_REVIEW,
    STATUS_PROHIBITED_REVIEW,
    STATUS_RA_PROHIBITED,
    NON_SUPPORTING,
    standard_scope,
)
from .text_utils import match_key


def result_visual(status: str) -> tuple[str, str]:
    """Return the presentation class/icon for a result status."""
    if status in (STATUS_NO_USE, STATUS_NO_USE_RSPO):
        return "result-red", "⛔"
    if status in (STATUS_RA_PROHIBITED, STATUS_PROHIBITED_REVIEW):
        return "result-red-review", "⚠️"
    if status in (STATUS_MITIGATION, STATUS_MITIGATION_REVIEW):
        return "result-pink", "⚠️"
    if status in (
        STATUS_OBSOLETE,
        STATUS_OBSOLETE_REVIEW,
        STATUS_MATCH_REVIEW,
    ):
        return "result-orange", "⚠️"
    if status == STATUS_DOCUMENT_REVIEW:
        return "result-yellow", "📄"
    if status == STATUS_IDENTITY_REVIEW:
        return "result-purple", "🔎"
    if status == STATUS_NO_MATCH:
        return "result-green", "✓"
    return "result-neutral", "•"


def screening_identity_summary(screening_identity: dict | None) -> str:
    """Build a concise, non-inferential summary of the identity screened."""
    identity = screening_identity or {}
    active_items = identity.get("active_ingredients", [])
    composition_items = identity.get("composition_components", [])
    document_cas = list(identity.get("document_cas", []))
    manual_cas = list(identity.get("manual_cas", []))

    parts: list[str] = []
    paired_cas: set[str] = set()

    if active_items:
        values = []
        for item in active_items:
            name = str(item.get("name", "")).strip()
            cas = str(item.get("cas", "")).strip()
            if not name:
                continue
            if cas:
                paired_cas.add(cas)
                values.append(f"{name} (CAS {cas})")
            else:
                values.append(name)
        if values:
            label = (
                "Ingredientes activos evaluados"
                if len(values) > 1
                else "Ingrediente activo evaluado"
            )
            parts.append(f"{label}: " + "; ".join(values))

    if composition_items:
        values = []
        seen_components: set[tuple[str, str]] = set()
        for item in composition_items:
            name = str(item.get("name", "")).strip()
            cas = str(item.get("cas", "")).strip()
            key = (name.casefold(), cas)
            if not name or key in seen_components:
                continue
            seen_components.add(key)
            if cas:
                paired_cas.add(cas)
                values.append(f"{name} (CAS {cas})")
            else:
                values.append(name)
        if values:
            label = (
                "Componentes de composición evaluados"
                if len(values) > 1
                else "Componente de composición evaluado"
            )
            parts.append(f"{label}: " + "; ".join(values))

    remaining_document_cas = [
        cas for cas in document_cas
        if cas not in paired_cas
    ]
    if remaining_document_cas:
        label = "CAS evaluados" if len(remaining_document_cas) > 1 else "CAS evaluado"
        parts.append(f"{label}: " + "; ".join(remaining_document_cas))

    remaining_manual_cas = [
        cas for cas in manual_cas
        if cas not in paired_cas and cas not in remaining_document_cas
    ]
    if remaining_manual_cas:
        label = (
            "CAS manuales evaluados"
            if len(remaining_manual_cas) > 1
            else "CAS manual evaluado"
        )
        parts.append(f"{label}: " + "; ".join(remaining_manual_cas))

    return ". ".join(parts)


def comparison_basis_summary(result: dict | None) -> str:
    """Describe the concrete identity/basis compared in the result card.

    Prefer confirmed active-ingredient identity. If that role is not confirmed,
    fall back to the CAS actually used for the regulatory-list match rather
    than labeling the matched list substance as an active ingredient.
    """
    result = result or {}
    identity = result.get("screening_identity") or {}

    active_items = identity.get("active_ingredients", [])
    if active_items:
        values = []
        seen = set()
        for item in active_items:
            name = str(item.get("name", "")).strip()
            cas = str(item.get("cas", "")).strip()
            key = (name.casefold(), cas)
            if not name or key in seen:
                continue
            seen.add(key)
            values.append(f"{name} (CAS {cas})" if cas else name)
        if values:
            label = (
                "Ingredientes activos evaluados"
                if len(values) > 1
                else "Ingrediente activo evaluado"
            )
            return f"{label}: " + "; ".join(values)

    hits = list(result.get("display_hits") or result.get("all_hits") or [])
    active_hits = []
    for hit in hits:
        if getattr(hit, "channel", "") == "ACTIVE_IDENTITY" or getattr(
            hit, "context_class", ""
        ) == "ACTIVE":
            active_hits.append(hit)

    if active_hits:
        values = []
        seen = set()
        for hit in active_hits:
            name = str(hit.entry.ingredient or "").strip()
            cas = str(hit.entry.cas or "").strip()
            key = (name.casefold(), cas)
            if not name or key in seen:
                continue
            seen.add(key)
            values.append(f"{name} (CAS {cas})" if cas else name)
        if values:
            label = (
                "Ingredientes activos evaluados"
                if len(values) > 1
                else "Ingrediente activo evaluado"
            )
            return f"{label}: " + "; ".join(values)

    # If identity is still under review, do not call the list substance an
    # active ingredient. Show the exact CAS used for the regulatory comparison
    # when one exists.
    cas_values = []
    seen_cas = set()
    for hit in hits:
        if getattr(hit, "strength", "") != "validated_cas":
            continue
        cas = str(hit.entry.cas or getattr(hit, "matched_value", "") or "").strip()
        if not cas or cas in seen_cas:
            continue
        seen_cas.add(cas)
        name = str(hit.entry.ingredient or "").strip()
        cas_values.append(f"{cas} ({name})" if name else cas)

    if cas_values:
        label = "CAS evaluados" if len(cas_values) > 1 else "CAS evaluado"
        return f"{label}: " + "; ".join(cas_values)

    # When the document already supplied contextual CAS in active/composition
    # evidence, prefer those concrete identifiers over an unrelated nominal
    # list hit elsewhere in the SDS (for example hydrogen cyanide listed only
    # as a combustion product). This is the actual chemical basis screened.
    contextual_cas = []
    seen_contextual_cas = set()
    for cas in list(identity.get("document_cas", [])) + list(
        identity.get("manual_cas", [])
    ):
        value = str(cas or "").strip()
        if not value or value in seen_contextual_cas:
            continue
        seen_contextual_cas.add(value)
        contextual_cas.append(value)

    if contextual_cas:
        label = "CAS evaluados" if len(contextual_cas) > 1 else "CAS evaluado"
        return f"{label}: " + "; ".join(contextual_cas)

    # Nominal/group review states still need to tell the user exactly what
    # reference identity drove the comparison, but only if that mention is
    # documentary support for product identity. Decomposition/combustion,
    # toxicology/reference, negation and incidental mentions must never become
    # the result-card identity.
    matched_entries = []
    seen_entries = set()
    has_group = False
    for hit in hits:
        if getattr(hit, "context_class", "") in NON_SUPPORTING:
            continue
        strength = str(getattr(hit, "strength", "") or "")
        if strength not in {
            "exact_name",
            "group_candidate",
            "group_deterministic",
        }:
            continue
        name = str(getattr(hit.entry, "ingredient", "") or "").strip()
        if not name:
            continue
        key = name.casefold()
        if key in seen_entries:
            continue
        seen_entries.add(key)
        matched_entries.append(name)
        has_group = has_group or bool(getattr(hit.entry, "is_group", False))

    if matched_entries:
        if has_group:
            label = (
                "Sustancias/grupos evaluados"
                if len(matched_entries) > 1
                else "Sustancia/grupo evaluado"
            )
        else:
            label = (
                "Sustancias evaluadas"
                if len(matched_entries) > 1
                else "Sustancia evaluada"
            )
        return f"{label}: " + "; ".join(matched_entries)

    fallback = screening_identity_summary(identity)
    return fallback


def pubchem_url(cas: str | None) -> str:
    value = (cas or "").strip()
    if not value or not is_valid_cas(value):
        return ""
    return f"https://pubchem.ncbi.nlm.nih.gov/#query={value}"


def cas_html(cas: str | None) -> str:
    value = escape(str(cas or "Varios"))
    url = pubchem_url(cas)
    if not url:
        return value
    return (
        f'<a href="{escape(url)}" target="_blank" '
        f'rel="noopener noreferrer">{value}</a>'
    )


def table_html(rows: list[dict]) -> str:
    if not rows:
        return ""

    columns = list(rows[0].keys())
    head = "".join(f"<th>{escape(str(column))}</th>" for column in columns)
    body_rows = []

    for row in rows:
        cells = "".join(
            (
                f"<td>{cas_html(row.get(column, ''))}</td>"
                if column == "CAS"
                else f"<td>{escape(str(row.get(column, '')))}</td>"
            )
            for column in columns
        )
        body_rows.append(f"<tr>{cells}</tr>")

    return (
        '<div class="clean-table-wrap"><table class="clean-table">'
        f"<thead><tr>{head}</tr></thead>"
        f"<tbody>{''.join(body_rows)}</tbody></table></div>"
    )


def scope_html(group: dict) -> str:
    if group["source_list"] != "PROHIBITED":
        return (
            "<b>Lectura por estándar:</b> RA: referencia específica de la lista "
            "· RSPO/ISCC: verificar requisito aplicable"
        )

    entry = SimpleNamespace(
        ingredient=group["ingredient"],
        criteria=group["criteria"],
    )
    scope = standard_scope(entry)
    rspo = (
        "criterio explícito aplicable"
        if scope["rspo"]
        else "sin equivalencia automática"
    )
    iscc = (
        "criterio explícito aplicable"
        if scope["iscc"]
        else "sin equivalencia automática"
    )
    return (
        "<b>Lectura por estándar:</b> "
        f"RSPO: {escape(rspo)} · ISCC: {escape(iscc)} · RA: prohibido"
    )


def criterion_summary_html(group: dict) -> str:
    signals = interpret_criteria(
        group.get("criteria", ""),
        group["source_list"],
    )
    if not signals:
        return ""

    items = "".join(
        f"<li><strong>{escape(signal.label)}</strong> — "
        f"{escape(signal.explanation)}</li>"
        for signal in signals
    )
    return (
        '<div class="criterion-summary">'
        '<div class="criterion-summary-title">Criterio identificado</div>'
        f"<ul>{items}</ul></div>"
    )


def composition_items_not_already_active(
    active_items,
    composition_items,
):
    """Hide composition rows already represented as confirmed active identity."""
    active_names = {
        key
        for item in active_items
        if (key := match_key(item.name))
    }
    active_cas = {item.cas for item in active_items if item.cas}

    return [
        item
        for item in composition_items
        if (not item.cas or item.cas not in active_cas)
        and match_key(item.name) not in active_names
    ]
