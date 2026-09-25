from __future__ import annotations
from html import escape
from pathlib import Path
import streamlit as st
from src.engine import analyze
from src.rules import STATUS_NO_USE,STATUS_MATCH_REVIEW,STATUS_DOCUMENT_REVIEW

BASE_DIR=Path(__file__).resolve().parent
MASTER_PATH=BASE_DIR/'data'/'master_restrictions.csv'
st.set_page_config(page_title='Evaluador de PROHIBIDOS',page_icon='🔎',layout='wide')

st.markdown("""
<style>
.block-container{max-width:1120px;padding-top:2rem;padding-bottom:4rem}
.hero{padding:1.2rem 1.35rem;border:1px solid #30363d;border-radius:14px;margin-bottom:1.2rem;background:rgba(255,255,255,.025)}
.hero h1{margin:0 0 .35rem 0;font-size:2rem}.hero p{margin:0;opacity:.78}
.result-card{padding:1.25rem 1.35rem;border-radius:14px;margin:1rem 0 1.35rem;border-left:8px solid}
.result-card h2{margin:0 0 .45rem;font-size:1.55rem}.result-card p{margin:0;line-height:1.55}
.result-red{background:#3a1518;border-color:#ef4444}.result-orange{background:#3b2512;border-color:#f97316}
.result-yellow{background:#38320f;border-color:#eab308}.result-neutral{background:#17212b;border-color:#64748b}
.match-box{border:1px solid #343a40;border-radius:12px;padding:1rem 1.1rem;margin:.65rem 0;background:rgba(255,255,255,.02)}
.match-title{font-size:1.08rem;font-weight:700;margin-bottom:.3rem}.match-meta{opacity:.82;font-size:.92rem}
div[data-testid="stFileUploader"] section{border-radius:12px}div.stButton>button{border-radius:10px;min-height:3rem;font-weight:650}
</style>
""",unsafe_allow_html=True)

st.markdown("""<div class="hero"><h1>🔎 Evaluador de Agroquímicos</h1>
<p>Busca evidencia documental contra la hoja <b>PROHIBIDOS</b>. La ausencia de coincidencias no significa que el producto sea seguro, autorizado o permitido.</p></div>""",unsafe_allow_html=True)

st.markdown("### 1. Documentos")
files=st.file_uploader('Cargue ficha técnica, ficha de datos de seguridad o ambos PDF',type=['pdf'],accept_multiple_files=True,help='Puede cargar varios documentos del mismo producto.')

with st.expander('2. Entrada manual de CAS · opcional'):
    manual=st.text_area('CAS manual (uno o varios)',placeholder='Ejemplo: 153719-23-4')
    manual_active=st.checkbox('Confirmo que los CAS manuales corresponden a ingrediente(s) activo(s)',value=False,help='Sin esta confirmación, un CAS de PROHIBIDOS genera una alerta naranja para revisión.')

def result_card(status,message):
    if status==STATUS_NO_USE: css,icon='result-red','⛔'
    elif status==STATUS_MATCH_REVIEW: css,icon='result-orange','⚠️'
    elif status==STATUS_DOCUMENT_REVIEW: css,icon='result-yellow','📄'
    else: css,icon='result-neutral','✓'
    st.markdown(f'<div class="result-card {css}"><h2>{icon} {escape(status)}</h2><p>{escape(message)}</p></div>',unsafe_allow_html=True)

def consolidated_hits(hits):
    grouped={}
    for h in hits:
        key=(h.entry.ingredient,h.entry.cas,h.source_file,h.channel)
        g=grouped.setdefault(key,{'ingredient':h.entry.ingredient,'cas':h.entry.cas or 'Varios','file':h.source_file,'channel':h.channel,'pages':set(),'classes':set(),'usage':h.entry.usage,'criteria':h.entry.criteria,'contexts':[]})
        if h.page:g['pages'].add(h.page)
        g['classes'].add(h.context_class)
        if h.context and h.context not in g['contexts']:g['contexts'].append(h.context)
    return list(grouped.values())

if st.button('Evaluar contra PROHIBIDOS',type='primary',use_container_width=True):
    items=[(f.name,f.getvalue()) for f in (files or [])]
    if not items and not manual.strip():
        st.warning('Cargue al menos un PDF o introduzca un CAS.');st.stop()
    with st.spinner('Analizando documentos y cruzando con PROHIBIDOS...'):
        result=analyze(items,manual_cas_text=manual,manual_active_confirmed=manual_active,master_path=MASTER_PATH)
    ev=result['evaluation'];result_card(ev.status,ev.message)

    if ev.status==STATUS_MATCH_REVIEW:
        st.caption('La coincidencia con PROHIBIDOS es real; lo pendiente es confirmar el papel de la sustancia dentro del producto.')
    elif ev.status==STATUS_DOCUMENT_REVIEW:
        st.caption('No existe una coincidencia demostrada. La revisión se solicita porque el documento no pudo evaluarse de forma suficiente.')

    if ev.hits:
        st.markdown('### Evidencia que determina el resultado')
        for g in consolidated_hits(ev.hits):
            pages=', '.join(map(str,sorted(g['pages']))) if g['pages'] else '—';classes=', '.join(sorted(g['classes']))
            st.markdown(f'<div class="match-box"><div class="match-title">{escape(g["ingredient"])}</div><div class="match-meta"><b>CAS:</b> {escape(g["cas"])} &nbsp;·&nbsp; <b>Canal:</b> {escape(g["channel"])} &nbsp;·&nbsp; <b>Documento:</b> {escape(g["file"])} &nbsp;·&nbsp; <b>Página(s):</b> {escape(pages)}</div><div class="match-meta"><b>Contexto:</b> {escape(classes)}</div></div>',unsafe_allow_html=True)
            with st.expander(f'Ver detalle y contexto — {g["ingredient"]}'):
                if g['usage']:st.write('**Uso en PROHIBIDOS:**',g['usage'])
                if g['criteria']:st.write('**Criterio en PROHIBIDOS:**',g['criteria'])
                for i,context in enumerate(g['contexts'][:5],1):
                    st.caption(f'Ocurrencia {i}');st.write(context)

    if result['manual_invalid']:st.warning('CAS manuales descartados por formato/checksum: '+', '.join(result['manual_invalid']))
    for w in ev.warnings:st.info(w)

    with st.expander('Detalles técnicos y trazabilidad'):
        c1,c2,c3=st.columns(3);c1.metric('PROHIBIDOS con CAS',result['prohibited_specific_count']);c2.metric('Grupos / CAS varios',result['prohibited_group_count']);c3.metric('CAS válidos procesados',len(ev.cas_records))
        if result['documents']:
            st.markdown('#### Documentos')
            st.dataframe([{'Archivo':d.file_name,'Páginas':d.page_count,'Caracteres':d.character_count,'Páginas con texto':d.pages_with_text,'Texto extraíble':'Sí' if d.processable else 'No'} for d in result['documents']],use_container_width=True,hide_index=True)
        if result['all_hits']:
            st.markdown('#### Todas las coincidencias candidatas')
            st.dataframe([{'Entrada PROHIBIDOS':h.entry.ingredient,'CAS':h.entry.cas or 'Varios','Canal':h.channel,'Valor':h.matched_value,'Clase contextual':h.context_class,'Archivo':h.source_file,'Página':h.page or '—'} for h in result['all_hits']],use_container_width=True,hide_index=True)
        if ev.cas_records:
            st.markdown('#### CAS válidos detectados/procesados')
            st.dataframe([{'CAS':r.cas,'Fuentes':', '.join(sorted({o.source_file for o in r.occurrences})),'Ocurrencias':len(r.occurrences)} for r in ev.cas_records],use_container_width=True,hide_index=True)
        if result['invalid_candidates']:
            st.markdown('#### Candidatos CAS descartados por checksum');st.dataframe(result['invalid_candidates'],use_container_width=True,hide_index=True)
