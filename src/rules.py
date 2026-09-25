from __future__ import annotations
from .context_classifier import ACTIVE,COMPOSITION,INCIDENTAL,NEGATED,DECOMPOSITION,REFERENCE
from .models import Evaluation

STATUS_NO_USE='NO UTILIZAR'
STATUS_MATCH_REVIEW='COINCIDENCIA CON PROHIBIDOS — REVISAR'
STATUS_DOCUMENT_REVIEW='REVISIÓN DOCUMENTAL'
STATUS_NO_MATCH='SIN COINCIDENCIAS CON PROHIBIDOS'
NON_SUPPORTING={INCIDENTAL,NEGATED,DECOMPOSITION,REFERENCE}

def evaluate_prohibited(cas_records,hits,warnings=None,unprocessables=0):
    warnings=list(warnings or [])
    strong=[]; ambiguous=[]; exact_cas=[]; by_entry={}
    for h in hits:
        by_entry.setdefault(h.entry.ingredient,[]).append(h)
        if h.strength=='validated_cas':
            exact_cas.append(h)
    for _,items in by_entry.items():
        active=[h for h in items if h.context_class==ACTIVE]
        supporting=[h for h in items if h.context_class not in NON_SUPPORTING]
        if any(h.strength in ('validated_cas','exact_name','group_deterministic') for h in active):
            strong.extend(active+[h for h in items if h.strength=='validated_cas' and h.context_class==COMPOSITION])
        elif any(h.strength=='validated_cas' for h in items) and any(h.strength=='exact_name' and h.context_class==ACTIVE for h in items):
            strong.extend(items)
        elif supporting:
            ambiguous.extend(supporting)
    if strong:
        names=sorted({h.entry.ingredient for h in strong})
        return Evaluation(STATUS_NO_USE,'Existe evidencia documental suficiente de que el producto contiene como ingrediente activo una entrada de PROHIBIDOS: '+', '.join(names)+'.',strong,cas_records,warnings)
    if exact_cas:
        names=sorted({h.entry.ingredient for h in exact_cas})
        return Evaluation(STATUS_MATCH_REVIEW,'Se encontró un CAS que coincide exactamente con PROHIBIDOS: '+', '.join(names)+'. No se confirmó automáticamente que corresponda al ingrediente activo; verifique la evidencia antes de continuar.',exact_cas,cas_records,warnings)
    if ambiguous:
        names=sorted({h.entry.ingredient for h in ambiguous})
        return Evaluation(STATUS_MATCH_REVIEW,'Se detectó una coincidencia nominal o de grupo con PROHIBIDOS que requiere confirmación humana: '+', '.join(names)+'.',ambiguous,cas_records,warnings)
    if unprocessables:
        return Evaluation(STATUS_DOCUMENT_REVIEW,f'{unprocessables} documento(s) no tienen texto extraíble suficiente. No se demostró una coincidencia, pero tampoco es válido concluir su ausencia.',[],cas_records,warnings)
    return Evaluation(STATUS_NO_MATCH,'No se encontró evidencia de coincidencia con la hoja PROHIBIDOS mediante los mecanismos disponibles.',[],cas_records,warnings)
