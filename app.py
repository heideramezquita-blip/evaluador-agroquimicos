from __future__ import annotations

from pathlib import Path

import streamlit as st

from src.engine import analyze
from src.rules import (
    STATUS_MITIGATION,
    STATUS_NO_CAS,
    STATUS_NO_MATCH,
    STATUS_NO_USE,
    STATUS_REVIEW,
)


BASE_DIR = Path(__file__).resolve().parent
MASTER_PATH = BASE_DIR / "data" / "master_restrictions.csv"

st.set_page_config(
    page_title="Evaluador de Agroquímicos",
    page_icon="🌱",
    layout="centered",
)

st.title("Evaluador de Agroquímicos")
st.caption(
    "Motor CAS-first: extrae y valida CAS, consulta la base maestra y aplica reglas trazables."
)

archivos = st.file_uploader(
    "Cargue una ficha técnica, hoja de seguridad o ambos documentos",
    type=["pdf"],
    accept_multiple_files=True,
)

st.subheader("CAS manual")
manual_cas = st.text_area(
    "Puede introducir uno o varios CAS en cualquier momento (separados por coma, punto y coma o salto de línea).",
    placeholder="Ejemplo: 153719-23-4\n91465-08-6",
)
manual_es_activo = st.checkbox(
    "Confirmo que TODOS los CAS introducidos manualmente corresponden a ingrediente(s) activo(s)",
    value=False,
    help=(
        "Esta confirmación solo afecta reglas cuyo alcance en la base exige ingrediente activo. "
        "Si no está seguro, déjela desmarcada."
    ),
)

analizar = st.button("Analizar", type="primary", use_container_width=True)

if analizar:
    file_items = [(f.name, f.getvalue()) for f in (archivos or [])]

    if not file_items and not manual_cas.strip():
        st.warning("Cargue al menos un PDF o introduzca un CAS manualmente.")
        st.stop()

    with st.spinner("Analizando CAS y comparando con la base maestra..."):
        result = analyze(
            file_items,
            manual_cas_text=manual_cas,
            manual_active_confirmed=manual_es_activo,
            master_path=MASTER_PATH,
            enable_name_fallback=True,
        )

    evaluation = result["evaluation"]

    if evaluation.status == STATUS_NO_USE:
        st.error(f"### {evaluation.status}\n{evaluation.message}")
    elif evaluation.status == STATUS_REVIEW:
        st.warning(f"### {evaluation.status}\n{evaluation.message}")
    elif evaluation.status == STATUS_MITIGATION:
        st.warning(f"### {evaluation.status}\n{evaluation.message}")
    elif evaluation.status == STATUS_NO_MATCH:
        st.info(f"### {evaluation.status}\n{evaluation.message}")
    elif evaluation.status == STATUS_NO_CAS:
        st.warning(f"### {evaluation.status}\n{evaluation.message}")
    else:
        st.info(f"### {evaluation.status}\n{evaluation.message}")

    if evaluation.matches:
        st.subheader("Coincidencias con la base")
        rows = []
        for match in evaluation.matches:
            rows.append(
                {
                    "CAS": match.cas,
                    "Sustancia en base": match.ingredient,
                    "Lista": match.source_list,
                    "Resultado de regla": match.applied_action,
                    "Criterio": match.criteria or "—",
                    "Ingrediente activo confirmado": "Sí" if match.active_confirmed else "No",
                    "Fuente": f"{match.source_code} V{match.source_version} ({match.source_date})",
                }
            )
        st.dataframe(rows, use_container_width=True, hide_index=True)

        for match in evaluation.matches:
            detail = match.rationale
            if match.active_evidence:
                detail += f" Evidencia de rol: {match.active_evidence}"
            if detail:
                st.caption(f"{match.cas} — {detail}")

    st.write(f"**CAS válidos procesados:** {len(evaluation.cas_records)}")

    for warning in evaluation.warnings:
        st.warning(warning)

    with st.expander("Trazabilidad / auditoría"):
        st.write(f"**CAS consultables en la base:** {result['database_searchable_cas']}")

        if result["documents"]:
            st.markdown("#### Diagnóstico de documentos")
            doc_rows = []
            for doc in result["documents"]:
                doc_rows.append(
                    {
                        "Archivo": doc.file_name,
                        "Páginas": doc.page_count,
                        "Caracteres extraídos": doc.character_count,
                        "Páginas con texto": doc.pages_with_text,
                        "Procesable": "Sí" if doc.processable else "No",
                    }
                )
            st.dataframe(doc_rows, use_container_width=True, hide_index=True)

        if result["active_names"]:
            st.markdown("#### Nombres explícitos de ingrediente activo usados solo como evidencia auxiliar")
            st.dataframe(result["active_names"], use_container_width=True, hide_index=True)

        if evaluation.cas_records:
            st.markdown("#### CAS detectados y evidencia")
            audit_rows = []
            for record in evaluation.cas_records:
                for occurrence in record.occurrences:
                    audit_rows.append(
                        {
                            "CAS": record.cas,
                            "Archivo": occurrence.source_file,
                            "Página": occurrence.page,
                            "Origen": occurrence.source,
                            "Rol local": occurrence.role,
                            "Contexto": occurrence.context,
                            "Nota": occurrence.note,
                        }
                    )
            st.dataframe(audit_rows, use_container_width=True, hide_index=True)

        if result["invalid_candidates"]:
            st.markdown("#### Candidatos CAS descartados")
            st.dataframe(result["invalid_candidates"], use_container_width=True, hide_index=True)

        if result["fallback_attempts"]:
            st.markdown("#### Resolución secundaria por nombre / PubChem")
            fallback_rows = []
            for item in result["fallback_attempts"]:
                fallback_rows.append(
                    {
                        "Nombre": item.get("name"),
                        "Archivo": item.get("source_file"),
                        "Página": item.get("page"),
                        "Estado": item.get("estado"),
                        "CID": item.get("cid"),
                        "CAS": item.get("cas"),
                        "Mensaje": item.get("mensaje"),
                    }
                )
            st.dataframe(fallback_rows, use_container_width=True, hide_index=True)
