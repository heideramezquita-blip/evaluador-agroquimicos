import streamlit as st
import fitz  # PyMuPDF


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

    # -----------------------------
    # Información básica del archivo
    # -----------------------------

    tamano_bytes = archivo.size
    tamano_mb = tamano_bytes / (1024 * 1024)

    # El PDF permanece en memoria
    contenido_pdf = archivo.getvalue()

    st.success("Archivo recibido correctamente")

    st.write(f"**Archivo:** {archivo.name}")
    st.write(f"**Tamaño:** {tamano_mb:.2f} MB")
    st.write(f"**Tipo:** {archivo.type}")

    # -----------------------------
    # Extracción de texto
    # -----------------------------

    try:

        documento = fitz.open(
            stream=contenido_pdf,
            filetype="pdf"
        )

        numero_paginas = len(documento)

        paginas = []
        caracteres_por_pagina = []

        for numero_pagina, pagina in enumerate(documento, start=1):

            texto = pagina.get_text("text")
            texto = texto.strip()

            paginas.append(
                {
                    "pagina": numero_pagina,
                    "texto": texto
                }
            )

            caracteres_por_pagina.append(len(texto))

        texto_completo = "\n\n".join(
            pagina["texto"]
            for pagina in paginas
            if pagina["texto"]
        )

        total_caracteres = len(texto_completo)

        paginas_con_texto = sum(
            1 for cantidad in caracteres_por_pagina
            if cantidad > 0
        )

        paginas_sin_texto = (
            numero_paginas - paginas_con_texto
        )

        # -----------------------------
        # Diagnóstico
        # -----------------------------

        st.subheader("Diagnóstico del documento")

        st.write(f"**Número de páginas:** {numero_paginas}")
        st.write(f"**Caracteres extraídos:** {total_caracteres:,}")
        st.write(f"**Páginas con texto:** {paginas_con_texto}")
        st.write(f"**Páginas sin texto:** {paginas_sin_texto}")

        if total_caracteres == 0:

            st.error(
                "No se encontró texto extraíble. "
                "Este documento puede estar escaneado y requerir OCR "
                "o revisión manual."
            )

        else:

            st.success(
                "Se encontró texto extraíble en el documento."
            )

            with st.expander("Ver texto extraído"):

                for pagina in paginas:

                    if pagina["texto"]:

                        st.markdown(
                            f"### Página {pagina['pagina']}"
                        )

                        st.text(
                            pagina["texto"]
                        )

        documento.close()

    except Exception as error:

        st.error(
            "No fue posible procesar el PDF."
        )

        st.write(
            f"Detalle técnico: {error}"
        )

    st.info(
        "El archivo se procesa temporalmente en memoria "
        "y no se guarda de forma permanente."
    )
