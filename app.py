from __future__ import annotations
from html import escape
import streamlit as st
from src.engine import analyze
from src.evidence_presentation import (
    consolidate_evidence_hits,
    channel_label,
    context_label,
    evidence_pages,
    list_label,
    usage_label,
)
from src.normative_sources import reference_blocks_markdown, standards_scope_markdown
from src.rules import (
    STATUS_DOCUMENT_REVIEW,
    STATUS_IDENTITY_REVIEW,
    STATUS_MATCH_REVIEW,
    STATUS_MITIGATION_REVIEW,
    STATUS_OBSOLETE_REVIEW,
    STATUS_PROHIBITED_REVIEW,
)
from src.ui_helpers import (
    cas_html,
    comparison_basis_summary,
    composition_items_not_already_active,
    criterion_summary_html,
    result_visual,
    scope_html,
    table_html,
)
from src.ui_styles import APP_CSS

st.set_page_config(page_title='Evaluador de Agroquímicos',page_icon='🔎',layout='wide',initial_sidebar_state='collapsed')

st.markdown(APP_CSS, unsafe_allow_html=True)

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

def result_card(status, message, identity_summary=""):
    css, icon = result_visual(status)
    parts = message.split(' Resultado basado en ', 1)
    body = escape(parts[0])
    if len(parts) == 2:
        body += (
            '<span class="result-note">Resultado basado en '
            + escape(parts[1])
            + '</span>'
        )
    if identity_summary:
        body += (
            '<span class="result-identity">'
            + escape(identity_summary)
            + '</span>'
        )
    st.markdown(
        f'<div class="result-card {css}"><h2>{icon} {escape(status)}</h2>'
        f'<p>{body}</p></div>',
        unsafe_allow_html=True,
    )

if st.button('Evaluar documentos',type='primary',use_container_width=True):
    items=[(f.name,f.getvalue()) for f in (files or [])]
    if not items and not manual.strip():
        st.warning('Carga al menos un PDF o introduce un CAS para iniciar la evaluación.');st.stop()
    with st.spinner('Analizando documentos y cruzando con las listas normativas...'):
        result=analyze(items,manual_cas_text=manual,manual_active_confirmed=manual_active)
    ev=result['evaluation']
    st.markdown('<div class="divider"></div>',unsafe_allow_html=True)
    st.markdown('<div class="section-title">Resultado de la evaluación</div>',unsafe_allow_html=True)
    identity_summary=comparison_basis_summary(result)
    result_card(ev.status,ev.message,identity_summary)

    detected_items=result.get('detected_identities',[])
    reference_list_only=bool(detected_items) and all(
        item.get('contexts')==['REFERENCE_LIST']
        for item in detected_items
    )

    if detected_items:
        st.markdown('<div class="section-title">Coincidencias detectadas contra las listas</div>',unsafe_allow_html=True)
        st.caption(
            f'{len(detected_items)} identidad(es) única(s) de las bases locales '
            'fueron localizadas en el contenido analizado. Este inventario no '
            'implica por sí solo que sean ingredientes del producto.'
        )
        with st.expander(
            f'Ver inventario completo de coincidencias ({len(detected_items)})',
            expanded=len(detected_items)<=12,
        ):
            st.markdown(
                table_html([
                    {
                        'Lista': list_label(item.get('source_list','')),
                        'Identidad': item.get('ingredient',''),
                        'CAS': '; '.join(item.get('cas_values',[])) or 'Sin CAS específico',
                        'Contexto': ' · '.join(
                            context_label(value)
                            for value in item.get('contexts',[])
                        ),
                        'Documento(s)': '; '.join(item.get('files',[])),
                        'Página(s)': ', '.join(
                            str(page) for page in item.get('pages',[])
                        ) or '—',
                    }
                    for item in detected_items
                ]),
                unsafe_allow_html=True,
            )

    if reference_list_only:
        st.caption(
            'El documento fue reconocido como una lista o referencia normativa. '
            'Las coincidencias se enumeran para trazabilidad y no se atribuyen '
            'como composición de un producto.'
        )
    elif ev.status in (
        STATUS_MATCH_REVIEW,
        STATUS_PROHIBITED_REVIEW,
        STATUS_OBSOLETE_REVIEW,
        STATUS_MITIGATION_REVIEW,
    ):
        st.caption(
            'La coincidencia con la lista es real; lo pendiente es confirmar '
            'el papel de la sustancia dentro del producto.'
        )
    elif ev.status==STATUS_DOCUMENT_REVIEW:
        st.caption('No existe una coincidencia demostrada. La revisión se solicita porque el documento no pudo evaluarse de forma suficiente.')
    elif ev.status==STATUS_IDENTITY_REVIEW:
        st.caption('No hubo contenido documental o entrada manual suficiente para ejecutar el tamizaje dirigido contra las listas.')

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
    composition_items=composition_items_not_already_active(
        active_items,
        result.get('composition_components',[]),
    )

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
    st.markdown(standards_scope_markdown())

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
