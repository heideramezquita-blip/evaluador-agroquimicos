import streamlit as st

st.set_page_config(
    page_title="Evaluador de Agroquímicos",
    page_icon="🌱",
    layout="centered"
)

st.title("Evaluador de Agroquímicos")

st.write(
    "Herramienta para evaluar fichas técnicas y hojas de datos de seguridad "
    "de productos agroquímicos."
)

st.subheader("Cargue una ficha técnica o SDS")

archivo = st.file_uploader(
    "Seleccione un archivo PDF",
    type=["pdf"]
)

if archivo is not None:
    st.success(f"Archivo cargado: {archivo.name}")
    st.info("El análisis del documento se incorporará en la siguiente fase.")
