from __future__ import annotations
from html import escape
from pathlib import Path
import streamlit as st
from src.engine import analyze
from src.cas_utils import is_valid_cas
from src.criteria_presentation import interpret_criteria
from src.evidence_presentation import consolidate_evidence_hits
from src.evidence_presentation import (
    channel_label,
    context_label,
    evidence_pages,
    list_label,
    usage_label,
)
from src.normative_sources import reference_blocks_markdown
from src.rules import STATUS_NO_USE,STATUS_NO_USE_RSPO,STATUS_RA_PROHIBITED,STATUS_OBSOLETE,STATUS_MITIGATION,STATUS_MATCH_REVIEW,STATUS_DOCUMENT_REVIEW,STATUS_IDENTITY_REVIEW,standard_scope
from src.text_utils import match_key

BASE_DIR=Path(__file__).resolve().parent
MASTER_PATH=BASE_DIR/'data'/'master_restrictions.csv'
st.set_page_config(page_title='Evaluador de Agroquímicos',page_icon='🔎',layout='wide',initial_sidebar_state='collapsed')

st.markdown("""
<style>
:root{--accent:#e5322d;--ink:#161616;--muted:#667085;--line:#e7e7e7;--surface:#fff;--soft:#f7f7f8}
[data-testid="stAppViewContainer"]{background:#fff}
[data-testid="stHeader"]{background:rgba(255,255,255,.94);border-bottom:1px solid #eee}
.block-container{max-width:1040px;padding-top:2.1rem;padding-bottom:4.5rem}
.brand{display:flex;align-items:center;gap:.7rem;font-weight:800;font-size:1.05rem;color:var(--ink);margin-bottom:3.3rem}
.brand-mark{display:inline-flex;width:32px;height:32px;align-items:center;justify-content:center;border-radius:9px;background:var(--accent);color:#fff;font-size:17px}
.brand-badge{font-size:.72rem;font-weight:700;padding:.25rem .55rem;border-radius:999px;background:#f2f4f7;color:#475467}
.hero{text-align:center;max-width:820px;margin:0 auto 2rem}
.hero h1{font-size:2.55rem;letter-spacing:-.035em;line-height:1.1;margin:0 0 .75rem;color:var(--ink);font-weight:800}
.hero p{font-size:1.08rem;line-height:1.6;color:var(--muted);margin:0 auto;max-width:720px}
.upload-wrap{max-width:760px;margin:0 auto 1rem}
div[data-testid="stFileUploader"]{max-width:760px;margin:0 auto}
div[data-testid="stFileUploader"]>label{display:none}
div[data-testid="stFileUploader"] section{min-height:210px;border:2px dashed #d0d5dd!important;border-radius:16px!important;background:#fafafa!important;padding:2.2rem 1rem!important;transition:.18s ease}
div[data-testid="stFileUploader"] section:hover{border-color:var(--accent)!important;background:#fff8f7!important}
div[data-testid="stFileUploader"] section button{background:var(--accent)!important;color:#fff!important;border:0!important;border-radius:9px!important;font-weight:750!important;padding:.65rem 1.1rem!important}
div[data-testid="stFileUploader"] section button *,div[data-testid="stFileUploader"] section button p,div[data-testid="stFileUploader"] section button span,div[data-testid="stFileUploader"] section button svg{color:#fff!important;fill:#fff!important}
div[data-testid="stFileUploader"] section>div{width:100%!important;align-items:center!important;text-align:center!important}
div[data-testid="stFileUploader"] section [data-testid="stFileUploaderDropzoneInstructions"]{align-items:center!important;text-align:center!important}
div[data-testid="stFileUploader"] section [data-testid="stFileUploaderDropzoneInstructions"]>div{text-align:center!important}
div[data-testid="stFileUploader"] section button{margin-left:auto!important;margin-right:auto!important}
.helper{text-align:center;color:#667085;font-size:.9rem;font-weight:500;margin:.3rem 0 1.8rem}
.secondary{max-width:760px;margin:0 auto}
div[data-testid="stExpander"]{border:1px solid #d0d5dd;border-radius:12px;background:#fff} div[data-testid="stExpander"] summary,div[data-testid="stExpander"] summary *{color:#344054!important;font-weight:650!important;opacity:1!important} div[data-testid="stExpander"] svg{fill:#667085!important;color:#667085!important}
div.stButton{max-width:760px;margin:1.2rem auto 0}
div.stButton>button{min-height:3.2rem;border:0;border-radius:10px;font-size:1rem;font-weight:750;background:var(--accent)!important;color:#fff!important;box-shadow:0 4px 12px rgba(229,50,45,.18)}
div.stButton>button *,div.stButton>button p,div.stButton>button span,div.stButton>button svg{color:#fff!important;fill:#fff!important}
div.stButton>button:hover{background:#c92b27;color:#fff;border:0}
.divider{height:1px;background:#eee;margin:3rem 0 2rem}
.result-card{padding:1.35rem 1.45rem;border-radius:14px;margin:1rem 0 1.5rem;border:1px solid;border-left-width:7px}
.result-card h2{margin:0 0 .5rem;font-size:1.42rem}.result-card p{margin:0;line-height:1.58}.result-note{display:block;margin-top:.55rem;font-size:.9rem;color:#667085;font-weight:500}
.result-red{background:#fff2f1;border-color:#ef4444;color:#7f1d1d}
.result-orange{background:#fff6ed;border-color:#f97316;color:#7c2d12}
.result-yellow{background:#fffbeb;border-color:#eab308;color:#713f12}
.result-neutral{background:#f8fafc;border-color:#94a3b8;color:#334155}
.section-title{font-size:1.25rem;font-weight:800;color:var(--ink);margin:1.7rem 0 .8rem}
.match-box{border:1px solid #e4e7ec;border-radius:12px;padding:1rem 1.1rem;margin:.65rem 0;background:#fff;box-shadow:0 1px 2px rgba(16,24,40,.03)}
.match-title{font-size:1.05rem;font-weight:800;color:#101828;margin-bottom:.35rem}.match-meta{color:#475467;font-size:.92rem;line-height:1.6}.match-meta b{color:#344054;font-weight:750}.criterion-summary{margin:.7rem 0 0;padding:.7rem .8rem;border-radius:9px;background:#f8fafc;color:#344054;font-size:.9rem;line-height:1.5}.criterion-summary-title{font-weight:800;color:#101828;margin-bottom:.25rem}.criterion-summary ul{margin:.2rem 0 0;padding-left:1.1rem}.criterion-summary li+li{margin-top:.3rem}
[data-testid="stMetric"]{background:#fafafa;border:1px solid #eee;padding:.8rem;border-radius:10px}
/* Streamlit theme hardening: keep native widgets readable in light UI */
.stApp, .stApp p, .stApp label, .stApp span, .stApp div{color:#344054}
div[data-testid="stExpander"] details{background:#fff!important}
div[data-testid="stExpander"] details,div[data-testid="stExpander"] details>*{background:#fff!important;color:#344054!important}
div[data-testid="stExpander"] summary,div[data-testid="stExpander"] summary[aria-expanded="true"]{background:#f8fafc!important;color:#1f2937!important;border-radius:11px!important}
div[data-testid="stExpander"] summary:hover{background:#f2f4f7!important}
div[data-testid="stExpander"] summary p,div[data-testid="stExpander"] summary span,div[data-testid="stExpander"] summary svg{color:#1f2937!important;fill:#475467!important;font-weight:700!important}
div[data-testid="stExpander"] details>div,div[data-testid="stExpander"] details>div>div{background:#fff!important;color:#344054!important}
div[data-testid="stExpander"] details>div p,
div[data-testid="stExpander"] details>div label,
div[data-testid="stExpander"] details>div span,
div[data-testid="stExpander"] details>div strong,
div[data-testid="stExpander"] details>div div{color:#344054!important}
div[data-testid="stExpander"] details>div [data-testid="stMarkdownContainer"],
div[data-testid="stExpander"] details>div [data-testid="stMarkdownContainer"] *{color:#344054!important;background-color:transparent!important}
div[data-testid="stTextArea"] label p{color:#344054!important;font-weight:650!important}
div[data-testid="stTextArea"] textarea{background:#fff!important;color:#101828!important;border:1px solid #98a2b3!important}
div[data-testid="stTextArea"] textarea::placeholder{color:#667085!important;opacity:1!important}
div[data-testid="stCheckbox"] label p,div[data-testid="stCheckbox"] label span{color:#344054!important}
div[data-testid="stMetric"]{background:#f8fafc!important}
div[data-testid="stMetric"] label,div[data-testid="stMetric"] label p{color:#475467!important}
div[data-testid="stMetric"] [data-testid="stMetricValue"],div[data-testid="stMetric"] [data-testid="stMetricValue"] *{color:#101828!important}
[data-testid="stDataFrame"]{color:#101828!important;border:1px solid #dfe3e8!important;border-radius:12px!important;overflow:hidden!important;background:#fff!important;box-shadow:0 1px 2px rgba(16,24,40,.04)}
[data-testid="stDataFrame"] *{font-size:.9rem!important}
[data-testid="stDataFrame"] [role="columnheader"]{background:#f2f4f7!important;color:#344054!important;font-weight:750!important;border-color:#d0d5dd!important}
[data-testid="stDataFrame"] [role="columnheader"] *{color:#344054!important;font-weight:750!important}
[data-testid="stDataFrame"] [role="gridcell"]{background:#fff!important;color:#101828!important;border-color:#eaecf0!important}
[data-testid="stDataFrame"] [role="gridcell"] *{color:#101828!important}
[data-testid="stDataFrame"] [role="row"]:hover [role="gridcell"]{background:#f9fafb!important}
[data-testid="stDataFrame"] canvas{filter:none!important}
h1,h2,h3,h4{color:#101828!important}

/* File uploader: light file chips + centered empty-state controls */
div[data-testid="stFileUploader"] section{display:flex!important;flex-direction:column!important;justify-content:center!important;align-items:center!important}
div[data-testid="stFileUploader"] section>div{display:flex!important;flex-direction:column!important;justify-content:center!important;align-items:center!important;gap:.7rem!important;width:100%!important}
div[data-testid="stFileUploader"] section [data-testid="stFileUploaderDropzoneInstructions"]{display:flex!important;flex-direction:column!important;align-items:center!important;justify-content:center!important;text-align:center!important;width:auto!important}
div[data-testid="stFileUploader"] section [data-testid="stFileUploaderDropzoneInstructions"] *{text-align:center!important}
div[data-testid="stFileUploader"] section small{color:#667085!important;text-align:center!important}
div[data-testid="stFileUploader"] [data-testid="stFileUploaderFile"]{background:#fff!important;border:1px solid #d0d5dd!important;border-radius:10px!important;color:#344054!important;box-shadow:0 1px 2px rgba(16,24,40,.04)!important}
div[data-testid="stFileUploader"] [data-testid="stFileUploaderFile"] *{color:#344054!important}
div[data-testid="stFileUploader"] [data-testid="stFileUploaderFile"] button{background:#f2f4f7!important;border:1px solid #e4e7ec!important;color:#475467!important}
div[data-testid="stFileUploader"] [data-testid="stFileUploaderFile"] button *{color:#475467!important;fill:#475467!important}
div[data-testid="stFileUploader"] [data-testid="stFileUploaderFile"] button:hover{background:#fee4e2!important;border-color:#fda29b!important}
div[data-testid="stFileUploader"] [data-testid="stFileUploaderFile"] button:hover *{color:#b42318!important;fill:#b42318!important}

/* Uploaded-file document glyph: target Streamlit's icon container, not only the SVG */
div[data-testid="stFileUploader"] [data-testid="stFileUploaderFile"]>div:first-child,
div[data-testid="stFileUploader"] ul>li>div:first-child{
background:#f2f4f7!important;
color:#475467!important;
border-radius:8px!important;
}
div[data-testid="stFileUploader"] [data-testid="stFileUploaderFile"]>div:first-child *,
div[data-testid="stFileUploader"] ul>li>div:first-child *{
color:#475467!important;
fill:#475467!important;
}

/* Uploaded-file row: Streamlit renders this outside the dropzone in some versions */
div[data-testid="stFileUploader"] ul,
div[data-testid="stFileUploader"] ul>li,
div[data-testid="stFileUploader"] [data-testid="stFileUploaderFile"],
div[data-testid="stFileUploader"] [data-testid="stFileUploaderFile"]>div{
background:#fff!important;color:#344054!important;border-color:#d0d5dd!important}
div[data-testid="stFileUploader"] ul>li{border:1px solid #d0d5dd!important;border-radius:10px!important;box-shadow:0 1px 2px rgba(16,24,40,.04)!important}
div[data-testid="stFileUploader"] ul>li *,
div[data-testid="stFileUploader"] [data-testid="stFileUploaderFile"] *{color:#344054!important}

/* Uploaded document icon: Streamlit/BaseWeb may keep a dark theme background */
div[data-testid="stFileUploader"] [data-testid="stFileUploaderFile"] svg,
div[data-testid="stFileUploader"] ul>li svg{
color:#475467!important;
fill:#475467!important;
}
div[data-testid="stFileUploader"] [data-testid="stFileUploaderFile"] svg:first-of-type,
div[data-testid="stFileUploader"] ul>li svg:first-of-type{
background:#f2f4f7!important;
border-radius:8px!important;
}
div[data-testid="stFileUploader"] ul>li button,
div[data-testid="stFileUploader"] [data-testid="stFileUploaderFile"] button{background:#f2f4f7!important;color:#475467!important;border:1px solid #e4e7ec!important}
div[data-testid="stFileUploader"] ul>li button *,
div[data-testid="stFileUploader"] [data-testid="stFileUploaderFile"] button *{color:#475467!important;fill:#475467!important}

.clean-table-wrap{width:100%;overflow-x:auto;border:1px solid #dfe3e8;border-radius:12px;background:#fff;box-shadow:0 1px 2px rgba(16,24,40,.04);margin:.35rem 0 1.25rem}
.clean-table{width:100%;border-collapse:collapse;background:#fff;color:#101828;font-size:.9rem}
.clean-table th{background:#f2f4f7;color:#344054;font-weight:750;text-align:left;padding:.72rem .75rem;border-bottom:1px solid #d0d5dd;white-space:nowrap}
.clean-table td{background:#fff;color:#101828;padding:.72rem .75rem;border-bottom:1px solid #eaecf0;vertical-align:top}
.clean-table tr:last-child td{border-bottom:0}.clean-table tbody tr:hover td{background:#f9fafb}
footer{visibility:hidden}
@media(max-width:700px){.block-container{padding-top:1.2rem}.brand{margin-bottom:2.2rem}.hero h1{font-size:2rem}.hero p{font-size:.98rem}}
</style>
""",unsafe_allow_html=True)

st.markdown('<div class="brand"><span class="brand-mark">A</span><span>Evaluador de Agroquímicos</span><span class="brand-badge">RSPO · ISCC · RA</span></div>',unsafe_allow_html=True)
st.markdown("""<div class="hero"><h1>Evalúa tus documentos contra las listas de plaguicidas</h1>
<p>Carga la ficha técnica, la ficha de datos de seguridad o ambas. El sistema identifica coincidencias documentales y prioriza su lectura frente a los criterios de plaguicidas de RSPO e ISCC; las listas de Rainforest Alliance se conservan como base local de detección y referencia complementaria.</p></div>""",unsafe_allow_html=True)

files=st.file_uploader('Seleccionar archivos PDF',type=['pdf'],accept_multiple_files=True,help='Puede cargar varios documentos del mismo producto.')
st.markdown('<div class="helper">Selecciona los PDF o arrástralos y suéltalos aquí · Puedes cargar FT + FDS del mismo producto</div>',unsafe_allow_html=True)

st.markdown('<div class="secondary">',unsafe_allow_html=True)
with st.expander('Introducir CAS manualmente · opcional'):
    manual=st.text_area('CAS manual (uno o varios)',placeholder='Ejemplo: 4685-14-7',help='Puede separar varios CAS con espacios, comas o saltos de línea.')
    manual_active=st.checkbox('Confirmo que los CAS manuales corresponden a ingrediente(s) activo(s)',value=False,help='Sin esta confirmación, una coincidencia con PROHIBIDOS se presenta como alerta para revisión.')
st.markdown('</div>',unsafe_allow_html=True)

def result_card(status,message):
    if status in (STATUS_NO_USE,STATUS_NO_USE_RSPO): css,icon='result-red','⛔'
    elif status in (STATUS_RA_PROHIBITED,STATUS_OBSOLETE,STATUS_MATCH_REVIEW,STATUS_MITIGATION): css,icon='result-orange','⚠️'
    elif status in (STATUS_DOCUMENT_REVIEW,STATUS_IDENTITY_REVIEW): css,icon='result-yellow','📄'
    else: css,icon='result-neutral','✓'
    parts=message.split(' Resultado basado en ',1)
    body=escape(parts[0])
    if len(parts)==2:
        body+=f'<span class="result-note">Resultado basado en {escape(parts[1])}</span>'
    st.markdown(f'<div class="result-card {css}"><h2>{icon} {escape(status)}</h2><p>{body}</p></div>',unsafe_allow_html=True)

def pubchem_url(cas):
    cas=(cas or '').strip()
    if not cas or not is_valid_cas(cas): return ''
    return 'https://pubchem.ncbi.nlm.nih.gov/#query='+cas

def cas_html(cas):
    value=escape(str(cas or 'Varios'))
    url=pubchem_url(cas)
    return f'<a href="{escape(url)}" target="_blank" rel="noopener noreferrer">{value}</a>' if url else value

def table_html(rows):
    if not rows:
        return ''
    columns=list(rows[0].keys())
    head=''.join(f'<th>{escape(str(col))}</th>' for col in columns)
    body=[]
    for row in rows:
        cells=''.join(f'<td>{cas_html(row.get(col,"")) if col=="CAS" else escape(str(row.get(col,"")))}</td>' for col in columns)
        body.append(f'<tr>{cells}</tr>')
    return '<div class="clean-table-wrap"><table class="clean-table"><thead><tr>'+head+'</tr></thead><tbody>'+''.join(body)+'</tbody></table></div>'

def scope_html(g):
    if g['source_list']!='PROHIBITED':
        return '<b>Lectura por estándar:</b> RA: referencia específica de la lista · RSPO/ISCC: verificar requisito aplicable'
    class EntryView:
        ingredient=g['ingredient']; criteria=g['criteria']
    scope=standard_scope(EntryView())
    rspo='criterio explícito aplicable' if scope['rspo'] else 'sin equivalencia automática'
    iscc='criterio explícito aplicable' if scope['iscc'] else 'sin equivalencia automática'
    return '<b>Lectura por estándar:</b> RSPO: '+escape(rspo)+' · ISCC: '+escape(iscc)+' · RA: prohibido'

def criterion_summary_html(g):
    signals=interpret_criteria(g.get('criteria',''),g['source_list'])
    if not signals:
        return ''
    items=''.join(
        f'<li><strong>{escape(signal.label)}</strong> — {escape(signal.explanation)}</li>'
        for signal in signals
    )
    return '<div class="criterion-summary"><div class="criterion-summary-title">Criterio identificado</div><ul>'+items+'</ul></div>'

if st.button('Evaluar documentos',type='primary',use_container_width=True):
    items=[(f.name,f.getvalue()) for f in (files or [])]
    if not items and not manual.strip():
        st.warning('Carga al menos un PDF o introduce un CAS para iniciar la evaluación.');st.stop()
    with st.spinner('Analizando documentos y cruzando con las listas normativas...'):
        result=analyze(items,manual_cas_text=manual,manual_active_confirmed=manual_active,master_path=MASTER_PATH)
    ev=result['evaluation']
    st.markdown('<div class="divider"></div>',unsafe_allow_html=True)
    st.markdown('<div class="section-title">Resultado de la evaluación</div>',unsafe_allow_html=True)
    result_card(ev.status,ev.message)

    if ev.status==STATUS_MATCH_REVIEW:
        st.caption('La coincidencia con la lista es real; lo pendiente es confirmar el papel de la sustancia dentro del producto.')
    elif ev.status==STATUS_DOCUMENT_REVIEW:
        st.caption('No existe una coincidencia demostrada. La revisión se solicita porque el documento no pudo evaluarse de forma suficiente.')
    elif ev.status==STATUS_IDENTITY_REVIEW:
        st.caption('El PDF es legible, pero no se encontró una identidad química suficientemente clara para sostener un resultado negativo contra las listas.')

    if result['display_hits']:
        st.markdown('<div class="section-title">Evidencia relevante</div>',unsafe_allow_html=True)
        for g in consolidate_evidence_hits(result['display_hits']):
            pages=evidence_pages(g); classes=' · '.join(context_label(x) for x in sorted(g['classes']))
            usage=usage_label(g['usage'])
            usage_html=f'<br><b>Uso principal:</b> {escape(usage)}' if usage else ''
            st.markdown(f'<div class="match-box"><div class="match-title">{escape(g["ingredient"])}</div><div class="match-meta"><b>Lista:</b> {escape(list_label(g["source_list"]))} &nbsp;·&nbsp; <b>CAS:</b> {cas_html(g["cas"])}{usage_html}<br><b>Evidencia:</b> {escape(classes)}<br><b>Documento:</b> {escape(g["file"])} &nbsp;·&nbsp; <b>Página(s) más relevante(s):</b> {escape(pages)}<br>{scope_html(g)}</div>{criterion_summary_html(g)}</div>',unsafe_allow_html=True)
            with st.expander(f'Ver evidencia documental — {g["ingredient"]}'):
                st.write('**Fuente:**',f'{list_label(g["source_list"])} · versión {g["source_version"]}')
                st.write('**Tipo de evidencia:**',classes)
                st.write('**Página(s) más relevante(s):**',pages)
                st.caption('La clasificación describe el criterio de la lista. El papel de la sustancia se evalúa aparte con la evidencia del documento; la concentración solo se confirma si el PDF la especifica.')
                st.caption('Para revisar el contenido completo y su contexto original, consulte directamente el PDF cargado.')

    active_items=result['active_ingredients']
    active_names={match_key(item.name) for item in active_items if match_key(item.name)}
    active_cas={item.cas for item in active_items if item.cas}
    composition_items=[
        item for item in result.get('composition_components',[])
        if (not item.cas or item.cas not in active_cas)
        and match_key(item.name) not in active_names
    ]

    if active_items or composition_items:
        st.markdown('<div class="section-title">Identidad documental detectada</div>',unsafe_allow_html=True)

    if active_items:
        st.markdown(
            table_html([
                {
                    'Ingrediente activo': item.name,
                    'Concentración': item.concentration or 'No extraída',
                    'CAS': item.cas or 'No detectado junto al ingrediente',
                    'Archivo': item.source_file,
                    'Página': item.page,
                }
                for item in active_items
            ]),
            unsafe_allow_html=True,
        )
        st.caption(
            'Ingredientes activos que el documento identifica explícitamente. La ausencia de CAS '
            'asociado no impide mostrar el ingrediente; solo indica que no se confirmó un CAS junto '
            'a esa evidencia documental.'
        )

    if composition_items:
        st.markdown('#### Componentes de composición detectados')
        st.markdown(
            table_html([
                {
                    'Componente': item.name,
                    'Concentración declarada': (
                        (item.concentration + ' %') if item.concentration else 'No extraída'
                    ),
                    'CAS': item.cas or 'No reconstruido',
                    'Archivo': item.source_file,
                    'Página': item.page,
                }
                for item in composition_items
            ]),
            unsafe_allow_html=True,
        )
        st.caption(
            'Estos nombres proceden de una tabla de composición de la FDS. Se muestran como identidad '
            'química documental, pero no se convierten automáticamente en ingredientes activos: una '
            'mezcla puede incluir solventes, sales, neutralizantes u otros componentes. Si una FT u '
            'otra evidencia explícita confirma el ingrediente activo, esa identidad se presenta arriba '
            'y puede enriquecerse con el CAS de la composición.'
        )

    if result['manual_invalid']:st.warning('CAS manuales descartados por formato/checksum: '+', '.join(result['manual_invalid']))
    for w in ev.warnings:st.info(w)

    with st.expander('Detalles técnicos y trazabilidad'):
        st.markdown('#### Base de referencia evaluada')
        c1,c2,c3,c4=st.columns(4)
        c1.metric('PROHIBIDOS',result['prohibited_specific_count']+result['prohibited_group_count'])
        c2.metric('OBSOLETOS',result['obsolete_count'])
        c3.metric('MITIGACIÓN',result['mitigation_count'])
        c4.metric('CAS válidos detectados',len(ev.cas_records))
        st.caption('Información de auditoría del análisis. No modifica el resultado mostrado arriba.')
        if result['documents']:
            st.markdown('#### Documentos')
            st.markdown(table_html([{'Archivo':d.file_name,'Páginas':d.page_count,'Caracteres':d.character_count,'Páginas con texto':d.pages_with_text,'Texto extraíble':'Sí' if d.processable else 'No'} for d in result['documents']]),unsafe_allow_html=True)
        if result['all_hits']:
            st.markdown('#### Coincidencias candidatas evaluadas')
            st.markdown(table_html([{'Lista':list_label(h.entry.source_list),'Sustancia':h.entry.ingredient,'CAS':h.entry.cas or 'Varios','Detección':channel_label(h.channel),'Evidencia':context_label(h.context_class),'Archivo':h.source_file,'Página':h.page or '—'} for h in result['all_hits']]),unsafe_allow_html=True)
        if ev.cas_records:
            st.markdown('#### CAS válidos detectados')
            st.markdown(table_html([{'CAS':r.cas,'Fuentes':', '.join(sorted({o.source_file for o in r.occurrences})),'Ocurrencias':len(r.occurrences)} for r in ev.cas_records]),unsafe_allow_html=True)
        if result['invalid_candidates']:
            st.markdown('#### Candidatos CAS descartados por checksum');st.markdown(table_html(result['invalid_candidates']),unsafe_allow_html=True)

with st.expander('Fuentes normativas y alcance de la evaluación'):
    st.markdown(reference_blocks_markdown())
    st.markdown('''**RSPO — marco principal:** [Principios y Criterios RSPO 2024, versión 4.2](https://rspo.org/wp-content/uploads/SPA-2024-RSPO-Principles-and-Criteria-%E2%80%93-Version-4.2-spanish.pdf), indicador 7.1.2 (C). La aplicación mapea como criterios explícitos: OMS Ia/Ib (también expresado como 1A/1B en el documento); carcinogenicidad, mutagenicidad o toxicidad reproductiva SGA 1A/1B; Convenios de Estocolmo o Rotterdam; y Paraquat. Las restricciones nacionales requieren verificación aparte.

**ISCC — marco principal:** [ISCC EU 202-2 v1.1](https://iscc-system.org/wp-content/uploads/dlm_uploads/2026/03/ISCC-EU-202-2-Agricultural-Biomass-ISCC-Principles-2-6.pdf) (válido desde el 1 de diciembre de 2022), requisito 2.4.1. La aplicación mapea los criterios explícitos verificados: OMS Ia/Ib, Convenio de Estocolmo y Anexo III del Convenio de Rotterdam. No amplía automáticamente ISCC a otros criterios.

**Rainforest Alliance — referencia complementaria y base local de detección:** [Anexo al capítulo Agricultura v1.4 (A-07-SCRL-B-FA)](https://knowledge.rainforest-alliance.org/docs/es/farming-annex-v14), listas de plaguicidas **prohibidos**, **obsoletos** y **sujetos a mitigación de riesgos**. **Última carga de la base local: septiembre de 2026.**

Los enlaces de la OMS y los convenios son referencias informativas; la aplicación no consulta sus listados en tiempo real ni importa sustancias desde ellos. Solo aplica a RSPO o ISCC las correspondencias explícitas codificadas para los criterios que ya constan en la base local.''')

with st.expander('Cómo interpretar los criterios de las listas'):
    st.markdown('''**OMS Ia/Ib:** peligrosidad aguda para la salud humana: Ia significa extremadamente peligroso e Ib, altamente peligroso. Es un sistema distinto del SGA.

**SGA 1A/1B:** la categoría debe leerse junto con la clase de peligro. Aquí se muestran, cuando están documentadas, las clases CMR: carcinogenicidad, mutagenicidad y toxicidad reproductiva.

**Protocolo de Montreal:** trata sustancias que agotan la capa de ozono.

**Rotterdam:** somete determinadas sustancias del Anexo III al procedimiento de consentimiento fundamentado previo (PIC) en el comercio internacional; no significa una prohibición universal.

**Estocolmo:** regula contaminantes orgánicos persistentes mediante eliminación (anexo A), restricción (anexo B) o reducción de liberaciones no intencionales (anexo C), según las condiciones y excepciones aplicables.

**Efectos graves:** criterio de Rainforest Alliance por alta incidencia de efectos adversos graves o irreversibles sobre la salud humana o el ambiente.

**Mitigación de riesgos:** Rainforest Alliance identifica plaguicidas cuyo uso requiere medidas adicionales para reducir riesgos específicos, por ejemplo para las personas, organismos acuáticos, vida silvestre o polinizadores. Su inclusión en esta lista no significa por sí sola que el plaguicida esté prohibido.

**Rainforest Alliance:** en esta aplicación, sus listas son una referencia complementaria; su inclusión no equivale automáticamente a una prohibición de RSPO o ISCC.''')

st.markdown('<div class="helper" style="margin-top:3rem">La herramienta prioriza el tamizaje frente a RSPO e ISCC y conserva Rainforest Alliance como referencia complementaria. No sustituye la verificación de excepciones, restricciones nacionales ni condiciones específicas del estándar.</div>',unsafe_allow_html=True)
