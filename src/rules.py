from __future__ import annotations

from .models import CasRecord, Evaluation, RestrictionMatch


STATUS_NO_USE = "NO UTILIZAR"
STATUS_REVIEW = "REVISIÓN MANUAL"
STATUS_MITIGATION = "REQUIERE MITIGACIÓN"
STATUS_NO_MATCH = "SIN COINCIDENCIAS RESTRICTIVAS EN LAS LISTAS EVALUADAS"
STATUS_NO_CAS = "NO FUE POSIBLE DETERMINAR UN CAS AUTOMÁTICAMENTE"


def apply_rules(cas_records: list[CasRecord], matches: list[RestrictionMatch], warnings: list[str] | None = None) -> Evaluation:
    warnings = list(warnings or [])
    has_no_use = False
    has_review = False
    has_mitigation = False

    for match in matches:
        requires_role = match.scope in {"ACTIVE_INGREDIENT", "ROLE_CONFIRMATION_REQUIRED"}
        role_ok = (not requires_role) or match.active_confirmed

        if match.action == "NO_UTILIZAR":
            if role_ok:
                match.applied_action = "NO_UTILIZAR"
                match.rationale = "Coincidencia CAS en lista de plaguicidas prohibidos y el CAS está confirmado como ingrediente activo."
                has_no_use = True
            else:
                match.applied_action = "REVISAR"
                match.rationale = "El CAS coincide con una lista cuyo alcance es ingrediente activo, pero el documento no confirma de forma suficiente que este CAS corresponda al ingrediente activo."
                has_review = True
        elif match.action == "REQUIERE_MITIGACION":
            if role_ok:
                match.applied_action = "MITIGAR"
                match.rationale = "Coincidencia CAS en la lista de plaguicidas para mitigar riesgo con rol de sustancia suficientemente confirmado."
                has_mitigation = True
            else:
                match.applied_action = "REVISAR"
                match.rationale = "El CAS coincide con la lista de mitigación, pero el Excel no establece que la regla deba aplicarse a cualquier coformulante y el rol de la sustancia no está suficientemente confirmado."
                has_review = True
        elif match.action == "REVISAR_OBSOLETO":
            match.applied_action = "REVISAR"
            match.rationale = "Coincidencia con el listado de plaguicidas obsoletos. La base no contiene una regla explícita que permita convertir automáticamente esta coincidencia en NO UTILIZAR."
            has_review = True
        else:
            match.applied_action = "INFORMATIVO"
            match.rationale = "Coincidencia informativa sin regla automática de restricción."

    if has_no_use:
        return Evaluation(status=STATUS_NO_USE,message="Se encontró al menos una coincidencia confirmada con la lista de plaguicidas prohibidos.",cas_records=cas_records,matches=matches,warnings=warnings)
    if has_review:
        return Evaluation(status=STATUS_REVIEW,message="Se encontraron coincidencias que requieren confirmar el rol de la sustancia o interpretar una lista sin regla automática de prohibición.",cas_records=cas_records,matches=matches,warnings=warnings)
    if has_mitigation:
        return Evaluation(status=STATUS_MITIGATION,message="No se encontró una prohibición confirmada, pero sí una coincidencia en la lista de plaguicidas para mitigar riesgo.",cas_records=cas_records,matches=matches,warnings=warnings)
    if cas_records:
        return Evaluation(status=STATUS_NO_MATCH,message="Se identificaron CAS válidos, pero no se encontraron coincidencias restrictivas en las listas evaluadas por CAS.",cas_records=cas_records,matches=matches,warnings=warnings)
    return Evaluation(status=STATUS_NO_CAS,message="No fue posible obtener un CAS válido de forma automática. Puede introducir el CAS manualmente.",cas_records=cas_records,matches=matches,warnings=warnings)
