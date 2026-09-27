from __future__ import annotations

from .context_classifier import (
    ACTIVE,
    COMPOSITION,
    DECOMPOSITION,
    INCIDENTAL,
    NEGATED,
    REFERENCE,
)
from .criteria_presentation import convention_codes, interpret_criteria
from .models import Evaluation


STATUS_NO_USE = "NO UTILIZAR — RSPO E ISCC"
STATUS_NO_USE_RSPO = "NO UTILIZAR — RSPO"
STATUS_RA_PROHIBITED = "ATENCIÓN — PROHIBIDO EN RA; REVISAR RSPO / ISCC"
STATUS_OBSOLETE = "ATENCIÓN — PLAGUICIDA OBSOLETO SEGÚN RA"
STATUS_MITIGATION = "ATENCIÓN — MITIGACIÓN DE RIESGOS SEGÚN RA"
STATUS_MATCH_REVIEW = "COINCIDENCIA NORMATIVA — REVISAR"
STATUS_DOCUMENT_REVIEW = "REVISIÓN DOCUMENTAL"
STATUS_IDENTITY_REVIEW = "REVISIÓN — IDENTIDAD QUÍMICA NO CONFIRMADA"
STATUS_NO_MATCH = "SIN COINCIDENCIAS DETECTADAS"

SOURCE_PROHIBITED = "PROHIBITED"
SOURCE_OBSOLETE = "OBSOLETE"
SOURCE_MITIGATION = "MITIGATE_RISK"

NON_SUPPORTING = {INCIDENTAL, NEGATED, DECOMPOSITION, REFERENCE}


def _strong_hits(items):
    active = [hit for hit in items if hit.context_class == ACTIVE]

    # A non-deterministic group-name hit is only a screening signal. It must
    # never become decisive merely because wording such as "arsenical" appears
    # near the active ingredient. Exact validated CAS evidence has priority;
    # CAS-less groups require an explicitly deterministic membership rule.
    decisive = [
        hit
        for hit in active
        if hit.strength in ("validated_cas", "exact_name", "group_deterministic")
    ]
    if decisive:
        composition_cas = [
            hit
            for hit in items
            if hit.strength == "validated_cas"
            and hit.context_class == COMPOSITION
        ]
        return decisive + composition_cas

    has_validated_cas = any(hit.strength == "validated_cas" for hit in items)
    has_active_exact_name = any(
        hit.strength == "exact_name" and hit.context_class == ACTIVE
        for hit in items
    )
    if has_validated_cas and has_active_exact_name:
        return items

    return []


def _strong_hits_by_source(hits) -> dict[str, list]:
    by_entry = {}
    for hit in hits:
        key = (hit.entry.source_list, hit.entry.ingredient, hit.entry.cas)
        by_entry.setdefault(key, []).append(hit)

    strong_by_source = {
        SOURCE_PROHIBITED: [],
        SOURCE_OBSOLETE: [],
        SOURCE_MITIGATION: [],
    }
    for (source_list, _, _), items in by_entry.items():
        strong_by_source.setdefault(source_list, []).extend(_strong_hits(items))

    return strong_by_source


def relevant_supporting_hits(hits) -> list:
    """Return all strong documentary matches across local reference lists.

    The final status keeps its severity/priority rules, but the evidence panel
    should not hide a lower-priority strong match (for example, a mitigation
    ingredient) merely because another ingredient in the same product triggers
    a prohibited-list status.
    """
    strong_by_source = _strong_hits_by_source(hits)
    relevant = []
    for source in (SOURCE_PROHIBITED, SOURCE_OBSOLETE, SOURCE_MITIGATION):
        relevant.extend(strong_by_source.get(source, []))
    return relevant


def standard_scope(entry):
    """Map an RA prohibited entry to criteria explicitly shared by RSPO/ISCC.

    A CMR word by itself is insufficient: the documented SGA category must be
    1A or 1B. Criterion parsing is shared with the UI to prevent semantic drift.
    """
    criteria = entry.criteria or ""
    ingredient = (entry.ingredient or "").casefold()
    signals = interpret_criteria(criteria, SOURCE_PROHIBITED)

    who_acute = any(
        signal.system == "OMS"
        and signal.hazard_class == "Toxicidad aguda"
        and signal.category in {"Ia", "Ib"}
        and signal.ra_hhp_criterion
        for signal in signals
    )
    cmr_signals = [
        signal
        for signal in signals
        if signal.system == "SGA"
        and signal.hazard_class
        in {"Carcinogenicidad", "Mutagenicidad", "Toxicidad reproductiva"}
        and signal.category in {"1A", "1B", "1A/1B"}
        and signal.ra_hhp_criterion
    ]

    conventions = set(convention_codes(criteria))
    stockholm = "E" in conventions
    rotterdam = "R" in conventions
    paraquat = "paraquat" in ingredient

    # RSPO P&C 2024 v4.2, 7.1.2(C): OMS Ia/Ib, SGA CMR 1A/1B,
    # Stockholm/Rotterdam, national restrictions and Paraquat.
    rspo = who_acute or bool(cmr_signals) or stockholm or rotterdam or paraquat
    # ISCC EU 202-2, 2.4.1: OMS Ia/Ib, Stockholm and Annex III Rotterdam.
    iscc = who_acute or stockholm or rotterdam

    rspo_basis = []
    iscc_basis = []
    if who_acute:
        rspo_basis.append("Toxicidad aguda · OMS Ia/Ib")
        iscc_basis.append("Toxicidad aguda · OMS Ia/Ib")
    for signal in cmr_signals:
        basis = f"SGA · {signal.hazard_class} {signal.category}"
        if basis not in rspo_basis:
            rspo_basis.append(basis)
    if stockholm:
        rspo_basis.append("Convenio de Estocolmo")
        iscc_basis.append("Convenio de Estocolmo")
    if rotterdam:
        rspo_basis.append("Convenio de Rotterdam")
        iscc_basis.append("Convenio de Rotterdam")
    if paraquat:
        rspo_basis.append("Paraquat")

    return {
        "rspo": rspo,
        "iscc": iscc,
        "ra": True,
        "rspo_basis": rspo_basis,
        "iscc_basis": iscc_basis,
    }


def _evaluate_strong_prohibited(strong_hits, cas_records, warnings) -> Evaluation:
    entries = {}
    for hit in strong_hits:
        entries[(hit.entry.ingredient, hit.entry.cas)] = hit.entry

    both = []
    rspo_only = []
    ra_only = []

    for entry in entries.values():
        scope = standard_scope(entry)
        if scope["rspo"] and scope["iscc"]:
            both.append(entry.ingredient)
        elif scope["rspo"]:
            rspo_only.append(entry.ingredient)
        else:
            ra_only.append(entry.ingredient)

    both = sorted(set(both))
    rspo_only = sorted(set(rspo_only))
    ra_only = sorted(set(ra_only))

    if both:
        message = (
            "Coincidencia con criterios explícitos de plaguicidas de RSPO e ISCC: "
            + ", ".join(both)
            + ". Rainforest Alliance también incluye el/los ingrediente(s) en su lista PROHIBIDOS."
        )
        if rspo_only:
            message += (
                " Coincidencia adicional aplicable de forma explícita a RSPO: "
                + ", ".join(rspo_only)
                + "."
            )
        if ra_only:
            message += (
                " Coincidencia adicional prohibida por Rainforest Alliance que requiere revisión específica frente a RSPO/ISCC: "
                + ", ".join(ra_only)
                + "."
            )
        return Evaluation(STATUS_NO_USE, message, strong_hits, cas_records, warnings)

    if rspo_only:
        message = (
            "Coincidencia con un criterio explícito de plaguicidas de RSPO: "
            + ", ".join(rspo_only)
            + ". Rainforest Alliance también incluye el/los ingrediente(s) en su lista PROHIBIDOS. Esta coincidencia no se traslada automáticamente como prohibición ISCC."
        )
        if ra_only:
            message += (
                " Coincidencia adicional prohibida por Rainforest Alliance que requiere revisión específica frente a RSPO/ISCC: "
                + ", ".join(ra_only)
                + "."
            )
        return Evaluation(
            STATUS_NO_USE_RSPO,
            message,
            strong_hits,
            cas_records,
            warnings,
        )

    names = ra_only or sorted({hit.entry.ingredient for hit in strong_hits})
    return Evaluation(
        STATUS_RA_PROHIBITED,
        "Rainforest Alliance incluye el/los ingrediente(s) en su lista PROHIBIDOS: "
        + ", ".join(names)
        + ". El criterio detectado no se trata como equivalencia automática de prohibición en RSPO o ISCC; revise el requisito aplicable antes de decidir su uso.",
        strong_hits,
        cas_records,
        warnings,
    )


def evaluate_prohibited(
    cas_records,
    hits,
    warnings=None,
    unprocessables=0,
    identity_basis=None,
):
    warnings = list(warnings or [])
    identity_basis = list(identity_basis or [])
    strong_by_source = _strong_hits_by_source(hits)

    strong_prohibited = strong_by_source[SOURCE_PROHIBITED]
    if strong_prohibited:
        return _evaluate_strong_prohibited(
            strong_prohibited,
            cas_records,
            warnings,
        )

    strong_obsolete = strong_by_source[SOURCE_OBSOLETE]
    if strong_obsolete:
        names = sorted({hit.entry.ingredient for hit in strong_obsolete})
        return Evaluation(
            STATUS_OBSOLETE,
            "Rainforest Alliance identifica como obsoleto el/los plaguicida(s): "
            + ", ".join(names)
            + ". Esta clasificación se conserva como alerta complementaria; la decisión frente a RSPO/ISCC debe verificarse con sus requisitos aplicables y la normativa nacional.",
            strong_obsolete,
            cas_records,
            warnings,
        )

    strong_mitigation = strong_by_source[SOURCE_MITIGATION]
    if strong_mitigation:
        names = sorted({hit.entry.ingredient for hit in strong_mitigation})
        return Evaluation(
            STATUS_MITIGATION,
            "Rainforest Alliance incluye este ingrediente en su lista de mitigación de riesgos: "
            + ", ".join(names)
            + ". Esta señal se presenta como referencia complementaria y no se convierte automáticamente en una prohibición RSPO o ISCC.",
            strong_mitigation,
            cas_records,
            warnings,
        )

    exact_cas = [hit for hit in hits if hit.strength == "validated_cas"]
    if exact_cas:
        names = sorted({hit.entry.ingredient for hit in exact_cas})
        lists = sorted({hit.entry.source_list for hit in exact_cas})
        return Evaluation(
            STATUS_MATCH_REVIEW,
            "Se encontró un CAS que coincide exactamente con una lista de referencia ("
            + ", ".join(lists)
            + "): "
            + ", ".join(names)
            + ". No se confirmó automáticamente que corresponda al ingrediente activo; verifique la evidencia antes de continuar.",
            exact_cas,
            cas_records,
            warnings,
        )

    ambiguous = [
        hit for hit in hits if hit.context_class not in NON_SUPPORTING
    ]
    if ambiguous:
        names = sorted({hit.entry.ingredient for hit in ambiguous})
        return Evaluation(
            STATUS_MATCH_REVIEW,
            "Se detectó una coincidencia nominal o de grupo en una lista de referencia que requiere confirmación humana: "
            + ", ".join(names)
            + ".",
            ambiguous,
            cas_records,
            warnings,
        )

    if unprocessables:
        return Evaluation(
            STATUS_DOCUMENT_REVIEW,
            f"{unprocessables} documento(s) no tienen texto extraíble suficiente. No se demostró una coincidencia, pero tampoco es válido concluir su ausencia.",
            [],
            cas_records,
            warnings,
        )

    if not identity_basis:
        return Evaluation(
            STATUS_IDENTITY_REVIEW,
            "El PDF contiene texto extraíble, pero no se identificó un CAS válido en contexto de ingrediente/composición ni una referencia explícita a ingrediente activo. Un encabezado de composición sin contenido químico extraíble no basta para sostener un resultado negativo. No es válido interpretar este resultado como ausencia de coincidencias en las listas.",
            [],
            cas_records,
            warnings,
        )

    basis = "; ".join(identity_basis)
    return Evaluation(
        STATUS_NO_MATCH,
        "Se identificó información química utilizable para el tamizaje ("
        + basis
        + "), pero no se detectaron coincidencias en las listas locales de referencia ni, por esta vía, con los criterios RSPO/ISCC mapeados. Resultado basado en la información disponible en los documentos analizados.",
        [],
        cas_records,
        warnings,
    )
