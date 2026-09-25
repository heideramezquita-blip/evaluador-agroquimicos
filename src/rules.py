from __future__ import annotations
from .context_classifier import ACTIVE,COMPOSITION,INCIDENTAL,NEGATED,DECOMPOSITION,REFERENCE
from .models import Evaluation

STATUS_NO_USE='NO UTILIZAR'
STATUS_OBSOLETE='NO UTILIZAR — PLAGUICIDA OBSOLETO'
STATUS_RA_SEVERE='ATENCIÓN — PROHIBIDO RA POR EFECTOS GRAVES'
STATUS_MITIGATION='ATENCIÓN — PLAGUICIDA SUJETO A MITIGACIÓN DE RIESGOS'
STATUS_MATCH_REVIEW='COINCIDENCIA NORMATIVA — REVISAR'
STATUS_DOCUMENT_REVIEW='REVISIÓN DOCUMENTAL'
STATUS_NO_MATCH='SIN COINCIDENCIAS DETECTADAS EN LOS DOCUMENTOS CARGADOS'
NON_SUPPORTING={INCIDENTAL,NEGATED,DECOMPOSITION,REFERENCE}

def _strong_hits(items):
    active=[h for h in items if h.context_class==ACTIVE]
    # A non-deterministic group-name hit is only a screening signal. It must
    # never become decisive merely because wording such as "arsenical" appears
    # near the active ingredient. Exact validated CAS evidence has priority;
    # CAS-less groups require an explicitly deterministic membership rule.
    decisive=[h for h in active if h.strength in ('validated_cas','exact_name','group_deterministic')]
    if decisive:
        return decisive+[h for h in items if h.strength=='validated_cas' and h.context_class==COMPOSITION]
    if any(h.strength=='validated_cas' for h in items) and any(h.strength=='exact_name' and h.context_class==ACTIVE for h in items):
        return items
    return []

def _severe_only(entry):
    parts=[x.strip() for x in entry.criteria.split(';') if x.strip()]
    return bool(parts) and all(x.startswith('Efectos graves') for x in parts)

def evaluate_prohibited(cas_records,hits,warnings=None,unprocessables=0):
    warnings=list(warnings or [])
    by_entry={}
    for h in hits:by_entry.setdefault((h.entry.source_list,h.entry.ingredient,h.entry.cas),[]).append(h)

    strong_prohibited=[]; strong_obsolete=[]; strong_mitigation=[]
    for (source_list,_,_),items in by_entry.items():
        strong=_strong_hits(items)
        if source_list=='PROHIBITED':strong_prohibited.extend(strong)
        elif source_list=='OBSOLETE':strong_obsolete.extend(strong)
        elif source_list=='MITIGATE_RISK':strong_mitigation.extend(strong)

    if strong_prohibited:
        severe=[h for h in strong_prohibited if _severe_only(h.entry)]
        other=[h for h in strong_prohibited if not _severe_only(h.entry)]
        if other:
            names=sorted({h.entry.ingredient for h in strong_prohibited})
            return Evaluation(STATUS_NO_USE,'Existe evidencia documental suficiente de ingrediente activo incluido en PROHIBIDOS. Aplica a Rainforest Alliance y, salvo el criterio exclusivo de Efectos graves, a la evaluación RSPO/ISCC: '+', '.join(names)+'.',strong_prohibited,cas_records,warnings)
        names=sorted({h.entry.ingredient for h in severe})
        return Evaluation(STATUS_RA_SEVERE,'Rainforest Alliance lo clasifica como prohibido exclusivamente por el criterio Efectos graves: '+', '.join(names)+'. Este criterio propio de RA no se traslada como prohibición a RSPO ni ISCC.',severe,cas_records,warnings)

    if strong_obsolete:
        names=sorted({h.entry.ingredient for h in strong_obsolete})
        return Evaluation(STATUS_OBSOLETE,'Rainforest Alliance prohíbe los plaguicidas obsoletos. Se identificó: '+', '.join(names)+'.',strong_obsolete,cas_records,warnings)

    if strong_mitigation:
        names=sorted({h.entry.ingredient for h in strong_mitigation})
        return Evaluation(STATUS_MITIGATION,'Rainforest Alliance incluye este ingrediente en la lista de mitigación de riesgos: '+', '.join(names)+'. Su uso solo procede dentro de una estrategia de MIP y con las medidas de mitigación aplicables completamente implementadas.',strong_mitigation,cas_records,warnings)

    exact_cas=[h for h in hits if h.strength=='validated_cas']
    if exact_cas:
        names=sorted({h.entry.ingredient for h in exact_cas})
        lists=sorted({h.entry.source_list for h in exact_cas})
        return Evaluation(STATUS_MATCH_REVIEW,'Se encontró un CAS que coincide exactamente con una lista normativa ('+', '.join(lists)+'): '+', '.join(names)+'. No se confirmó automáticamente que corresponda al ingrediente activo; verifique la evidencia antes de continuar.',exact_cas,cas_records,warnings)

    ambiguous=[h for h in hits if h.context_class not in NON_SUPPORTING]
    if ambiguous:
        names=sorted({h.entry.ingredient for h in ambiguous})
        return Evaluation(STATUS_MATCH_REVIEW,'Se detectó una coincidencia nominal o de grupo en una lista normativa que requiere confirmación humana: '+', '.join(names)+'.',ambiguous,cas_records,warnings)

    if unprocessables:
        return Evaluation(STATUS_DOCUMENT_REVIEW,f'{unprocessables} documento(s) no tienen texto extraíble suficiente. No se demostró una coincidencia, pero tampoco es válido concluir su ausencia.',[],cas_records,warnings)
    return Evaluation(STATUS_NO_MATCH,'No se identificó evidencia suficiente de coincidencia con PROHIBIDOS, OBSOLETOS o MITIGACIÓN DE RIESGOS a partir de la información disponible en los documentos cargados. Este resultado no confirma por sí mismo que el producto esté permitido.',[],cas_records,warnings)
