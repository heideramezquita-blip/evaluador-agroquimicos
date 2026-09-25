from __future__ import annotations
from pathlib import Path
import streamlit as st
from src.engine import analyze
from src.rules import STATUS_NO_USE,STATUS_REVIEW
BASE_DIR=Path(__file__).resolve().parent; MASTER_PATH=BASE_DIR/'data'/'master_restrictions.csv'
st.set_page_config(page_title='Evaluador de PROHIBIDOS',page_icon='🌱',layout='centered')
st.title('Evaluador de Agroquímicos')
st.caption('Detección documental conservadora contra la hoja PROHIBIDOS. No evalúa seguridad, autorización ni aptitud general del producto.')
files=st.file_uploader('Cargue ficha técnica, ficha de datos de seguridad o ambos PDF',type=['pdf'],accept_multiple_files=True)
with st.expander('Entrada manual de CAS'):
    manual=st.text_area('CAS manual (uno o varios)',placeholder='153719-23-4')
    manual_active=st.checkbox('Confirmo que los CAS manuales corresponden a ingrediente(s) activo(s)',value=False,help='Si no puede confirmar el rol, déjelo desmarcado; una coincidencia se enviará a revisión manual.')
if st.button('Evaluar contra PROHIBIDOS',type='primary',use_container_width=True):
    items=[(f.name,f.getvalue()) for f in (files or [])]
    if not items and not manual.strip():st.warning('Cargue al menos un PDF o introduzca un CAS.');st.stop()
    with st.spinner('Buscando evidencia en PROHIBIDOS...'):
        result=analyze(items,manual_cas_text=manual,manual_active_confirmed=manual_active,master_path=MASTER_PATH)
    ev=result['evaluation']
    if ev.status==STATUS_NO_USE:st.error(f'### {ev.status}\n{ev.message}')
    elif ev.status==STATUS_REVIEW:st.warning(f'### {ev.status}\n{ev.message}')
    else:st.info(f'### {ev.status}\n{ev.message}')
    if ev.hits:
        st.subheader('Evidencia relevante')
        rows=[]
        for h in ev.hits:
            rows.append({'Sustancia/grupo PROHIBIDOS':h.entry.ingredient,'CAS en PROHIBIDOS':h.entry.cas or 'Varios','Canal':h.channel,'Contexto clasificado':h.context_class,'Documento':h.source_file,'Página':h.page or '—','Uso':h.entry.usage or '—','Criterio':h.entry.criteria or '—'})
        st.dataframe(rows,use_container_width=True,hide_index=True)
        for h in ev.hits:
            with st.expander(f"Evidencia: {h.entry.ingredient} — {h.source_file} pág. {h.page or '—'}"):
                st.write(h.context);st.caption(h.rationale)
    for w in ev.warnings:st.warning(w)
    if result['manual_invalid']:st.warning('CAS manuales descartados por formato/checksum: '+', '.join(result['manual_invalid']))
    with st.expander('Trazabilidad técnica'):
        st.write(f"PROHIBIDOS con CAS específico: {result['prohibited_specific_count']}")
        st.write(f"PROHIBIDOS definidos como grupo/CAS varios: {result['prohibited_group_count']}")
        if result['documents']:
            st.dataframe([{'Archivo':d.file_name,'Páginas':d.page_count,'Caracteres':d.character_count,'Páginas con texto':d.pages_with_text,'Texto extraíble':'Sí' if d.processable else 'No'} for d in result['documents']],use_container_width=True,hide_index=True)
        if result['all_hits']:
            st.markdown('#### Todas las coincidencias candidatas')
            st.dataframe([{'Entrada':h.entry.ingredient,'Canal':h.channel,'Valor':h.matched_value,'Clase contextual':h.context_class,'Archivo':h.source_file,'Página':h.page or '—'} for h in result['all_hits']],use_container_width=True,hide_index=True)
        if ev.cas_records:
            st.markdown('#### CAS válidos detectados/procesados')
            st.dataframe([{'CAS':r.cas,'Fuentes':', '.join(sorted({o.source_file for o in r.occurrences}))} for r in ev.cas_records],use_container_width=True,hide_index=True)
        if result['invalid_candidates']:
            st.markdown('#### Candidatos CAS descartados por checksum')
            st.dataframe(result['invalid_candidates'],use_container_width=True,hide_index=True)
