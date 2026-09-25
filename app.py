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

    # Información básica del archivo
    tamano_bytes = archivo.size
    tamano_mb = tamano_bytes / (1024 * 1024)

    # Leer el archivo en memoria.
    # No se guarda en el repositorio ni se crea un archivo permanente.
    contenido_pdf = archivo.getvalue()

    st.success("Archivo recibido correctamente")

    st.write(f"**Archivo:** {archivo.name}")
    st.write(f"**Tamaño:** {tamano_mb:.2f} MB")
    st.write(f"**Tipo:** {archivo.type}")
    st.write(f"**Bytes recibidos:** {len(contenido_pdf):,}")

    st.info(
        "El archivo se mantiene únicamente para el procesamiento de esta sesión. "
        "La aplicación no lo guarda de forma permanente."
    )
