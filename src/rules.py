from __future__ import annotations
from .context_classifier import ACTIVE,INCIDENTAL,NEGATED,DECOMPOSITION,REFERENCE
from .models import Evaluation
STATUS_NO_USE='NO UTILIZAR'; STATUS_REVIEW='REVISIÓN MANUAL'; STATUS_NO_MATCH='SIN COINCIDENCIAS CON PROHIBIDOS'
NON_SUPPORTING={INCIDENTAL,NEGATED,DECOMPOSITION,REFERENCE}

def evaluate_prohibited(cas_records,hits,warnings=None,unprocessables=0):
    warnings=list(warnings or [])
    strong=[]; ambiguous=[]; by_entry={}
    for h in hits:by_entry.setdefault(h.entry.ingredient,[]).append(h)
    for name,items in by_entry.items():
        active=[h for h in items if h.context_class==ACTIVE]
        supporting=[h for h in items if h.context_class not in NON_SUPPORTING]
        if any(h.strength in ('validated_cas','exact_name','group_deterministic') for h in active):
            strong.extend(active)
        elif any(h.strength=='validated_cas' for h in items) and any(h.strength=='exact_name' and h.context_class==ACTIVE for h in items):
            strong.extend(items)
        elif supporting:
            ambiguous.extend(supporting)
    if strong:
        names=sorted({h.entry.ingredient for h in strong})
        return Evaluation(STATUS_NO_USE,'Evidencia documental suficiente de ingrediente activo incluido en PROHIBIDOS: '+', '.join(names)+'.',strong,cas_records,warnings)
    if ambiguous or unprocessables:
        reasons=[]
        if ambiguous:reasons.append('Se detectaron coincidencias con PROHIBIDOS cuyo contexto o pertenencia a grupo requiere confirmación humana.')
        if unprocessables:reasons.append(f'{unprocessables} documento(s) no tienen texto extraíble suficiente; no es válido concluir ausencia de coincidencias.')
        return Evaluation(STATUS_REVIEW,' '.join(reasons),ambiguous,cas_records,warnings)
    return Evaluation(STATUS_NO_MATCH,'No se encontró evidencia de coincidencia con la hoja PROHIBIDOS mediante los mecanismos disponibles.',[],cas_records,warnings)
