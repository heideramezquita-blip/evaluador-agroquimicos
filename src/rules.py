from __future__ import annotations
from .context_classifier import ACTIVE,COMPOSITION,INCIDENTAL,NEGATED,DECOMPOSITION,REFERENCE
from .models import Evaluation

STATUS_NO_USE='NO UTILIZAR — RSPO E ISCC'
STATUS_NO_USE_RSPO='NO UTILIZAR — RSPO'
STATUS_RA_PROHIBITED='ATENCIÓN — PROHIBIDO EN RA; REVISAR RSPO / ISCC'
STATUS_OBSOLETE='ATENCIÓN — PLAGUICIDA OBSOLETO SEGÚN RA'
STATUS_MITIGATION='ATENCIÓN — MITIGACIÓN DE RIESGOS SEGÚN RA'
STATUS_MATCH_REVIEW='COINCIDENCIA NORMATIVA — REVISAR'
STATUS_DOCUMENT_REVIEW='REVISIÓN DOCUMENTAL'
STATUS_NO_MATCH='SIN COINCIDENCIAS DETECTADAS'
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

def standard_scope(entry):
    """Map a Rainforest Alliance PROHIBITED entry to explicit RSPO/ISCC criteria.

    This is deliberately conservative: a Rainforest Alliance flag is not treated
    as proof of equivalence when the other standard does not state that criterion
    explicitly. National-law restrictions are outside this local mapping.
    """
    criteria=(entry.criteria or '').lower()
    ingredient=(entry.ingredient or '').lower()

    who_acute=('toxicidad aguda: 1a' in criteria or 'toxicidad aguda: 1b' in criteria)
    cmr=any(term in criteria for term in ('carcinogenicidad:', 'mutagenicidad:', 'toxicidad reproductiva:'))

    conventions=set()
    marker='convenciones internacionales:'
    if marker in criteria:
        raw=criteria.split(marker,1)[1].split(';',1)[0]
        conventions={x.strip().upper() for x in raw.replace(',',' ').split() if x.strip()}
    stockholm='E' in conventions
    rotterdam='R' in conventions
    paraquat='paraquat' in ingredient

    # RSPO P&C 2024 v4.2, 7.1.2(C): WHO 1A/1B, GHS CMR 1A/1B,
    # Stockholm/Rotterdam, national restrictions and paraquat.
    rspo=who_acute or cmr or stockholm or rotterdam or paraquat
    # ISCC EU 202-2, 2.4.1: WHO 1a/1b, Stockholm and Annex III Rotterdam.
    iscc=who_acute or stockholm or rotterdam

    rspo_basis=[]
    iscc_basis=[]
    if who_acute:
        rspo_basis.append('OMS 1A/1B'); iscc_basis.append('OMS 1A/1B')
    if cmr:
        rspo_basis.append('SGA CMR')
    if stockholm:
        rspo_basis.append('Estocolmo'); iscc_basis.append('Estocolmo')
    if rotterdam:
        rspo_basis.append('Rotterdam'); iscc_basis.append('Rotterdam')
    if paraquat:
        rspo_basis.append('Paraquat')

    return {
        'rspo':rspo,
        'iscc':iscc,
        'ra':True,
        'rspo_basis':rspo_basis,
        'iscc_basis':iscc_basis,
    }

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
        entries={}
        for h in strong_prohibited:
            entries[(h.entry.ingredient,h.entry.cas)]=h.entry

        both=[]; rspo_only=[]; ra_only=[]
        for entry in entries.values():
            scope=standard_scope(entry)
            if scope['rspo'] and scope['iscc']: both.append(entry.ingredient)
            elif scope['rspo']: rspo_only.append(entry.ingredient)
            else: ra_only.append(entry.ingredient)

        both=sorted(set(both)); rspo_only=sorted(set(rspo_only)); ra_only=sorted(set(ra_only))
        if both:
            message='Coincidencia con criterios explícitos de plaguicidas de RSPO e ISCC: '+', '.join(both)+'. Rainforest Alliance también incluye el/los ingrediente(s) en su lista PROHIBIDOS.'
            if rspo_only:
                message+=' Coincidencia adicional aplicable de forma explícita a RSPO: '+', '.join(rspo_only)+'.'
            if ra_only:
                message+=' Coincidencia adicional prohibida por Rainforest Alliance que requiere revisión específica frente a RSPO/ISCC: '+', '.join(ra_only)+'.'
            return Evaluation(STATUS_NO_USE,message,strong_prohibited,cas_records,warnings)

        if rspo_only:
            message='Coincidencia con un criterio explícito de plaguicidas de RSPO: '+', '.join(rspo_only)+'. Rainforest Alliance también incluye el/los ingrediente(s) en su lista PROHIBIDOS. Esta coincidencia no se traslada automáticamente como prohibición ISCC.'
            if ra_only:
                message+=' Coincidencia adicional prohibida por Rainforest Alliance que requiere revisión específica frente a RSPO/ISCC: '+', '.join(ra_only)+'.'
            return Evaluation(STATUS_NO_USE_RSPO,message,strong_prohibited,cas_records,warnings)

        names=ra_only or sorted({h.entry.ingredient for h in strong_prohibited})
        return Evaluation(
            STATUS_RA_PROHIBITED,
            'Rainforest Alliance incluye el/los ingrediente(s) en su lista PROHIBIDOS: '+', '.join(names)+'. El criterio detectado no se trata como equivalencia automática de prohibición en RSPO o ISCC; revise el requisito aplicable antes de decidir su uso.',
            strong_prohibited,cas_records,warnings
        )

    if strong_obsolete:
        names=sorted({h.entry.ingredient for h in strong_obsolete})
        return Evaluation(STATUS_OBSOLETE,'Rainforest Alliance identifica como obsoleto el/los plaguicida(s): '+', '.join(names)+'. Esta clasificación se conserva como alerta complementaria; la decisión frente a RSPO/ISCC debe verificarse con sus requisitos aplicables y la normativa nacional.',strong_obsolete,cas_records,warnings)

    if strong_mitigation:
        names=sorted({h.entry.ingredient for h in strong_mitigation})
        return Evaluation(STATUS_MITIGATION,'Rainforest Alliance incluye este ingrediente en su lista de mitigación de riesgos: '+', '.join(names)+'. Esta señal se presenta como referencia complementaria y no se convierte automáticamente en una prohibición RSPO o ISCC.',strong_mitigation,cas_records,warnings)

    exact_cas=[h for h in hits if h.strength=='validated_cas']
    if exact_cas:
        names=sorted({h.entry.ingredient for h in exact_cas})
        lists=sorted({h.entry.source_list for h in exact_cas})
        return Evaluation(STATUS_MATCH_REVIEW,'Se encontró un CAS que coincide exactamente con una lista de referencia ('+', '.join(lists)+'): '+', '.join(names)+'. No se confirmó automáticamente que corresponda al ingrediente activo; verifique la evidencia antes de continuar.',exact_cas,cas_records,warnings)

    ambiguous=[h for h in hits if h.context_class not in NON_SUPPORTING]
    if ambiguous:
        names=sorted({h.entry.ingredient for h in ambiguous})
        return Evaluation(STATUS_MATCH_REVIEW,'Se detectó una coincidencia nominal o de grupo en una lista de referencia que requiere confirmación humana: '+', '.join(names)+'.',ambiguous,cas_records,warnings)

    if unprocessables:
        return Evaluation(STATUS_DOCUMENT_REVIEW,f'{unprocessables} documento(s) no tienen texto extraíble suficiente. No se demostró una coincidencia, pero tampoco es válido concluir su ausencia.',[],cas_records,warnings)
    return Evaluation(STATUS_NO_MATCH,'No se identificaron coincidencias en las listas locales de referencia ni, por esta vía, con los criterios RSPO/ISCC mapeados. Resultado basado en la información disponible en los documentos analizados.',[],cas_records,warnings)
