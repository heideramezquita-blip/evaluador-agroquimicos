import re

import fitz
import streamlit as st

from src.ingredient_parser import detectar_bloques_composicion


# -------------------------------------------------
# Funciones CAS
# -------------------------------------------------

def validar_cas(cas):
    """
    Valida el dígito de control de un número CAS.
    Ejemplo válido: 131860-33-8
    """

    partes = cas.split("-")

    if len(partes) != 3:
        return False

    izquierda, centro, digito_control = partes

    if not (
        izquierda.isdigit()
        and centro.isdigit()
        and digito_control.isdigit()
    ):
        return False

    numeros = izquierda + centro

    suma = 0

    for multiplicador, digito in enumerate(
        reversed(numeros),
        start=1
    ):
        suma += int(digito) * multiplicador

    calculado = suma % 10

    return calculado == int(digito_control)


def extraer_cas(texto):
    """
    Busca cadenas con estructura de CAS y devuelve:
    - CAS válidos
    - candidatos CAS que no superan el dígito de control

    Se aceptan diferentes tipos de guion porque algunos PDF
    no extraen el guion ASCII estándar.
    """

    patron = re.compile(
        r"(?<!\d)"
        r"(\d{2,7})"
        r"\s*[-‐-‒–—−]\s*"
        r"(\d{2})"
        r"\s*[-‐-‒–—−]\s*"
        r"(\d)"
        r"(?!\d)"
    )

    validos = []
    invalidos = []

    for coincidencia in patron.finditer(texto):

        cas = (
            f"{coincidencia.group(1)}-"
            f"{coincidencia.group(2)}-"
            f"{coincidencia.group(3)}"
        )

        if validar_cas(cas):
            validos.append(cas)
        else:
            invalidos.append(cas)

    return validos, invalidos


# -------------------------------------------------
# Configuración Streamlit
# -------------------------------------------------

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


# -------------------------------------------------
# Procesamiento
# -------------------------------------------------

if archivo is not None:

    tamano_bytes = archivo.size
    tamano_mb = tamano_bytes / (1024 * 1024)

    contenido_pdf = archivo.getvalue()

    st.success("Archivo recibido correctamente")

    st.write(f"**Archivo:** {archivo.name}")
    st.write(f"**Tamaño:** {tamano_mb:.2f} MB")
    st.write(f"**Tipo:** {archivo.type}")

    try:

        documento = fitz.open(
            stream=contenido_pdf,
            filetype="pdf"
        )

        numero_paginas = len(documento)

        paginas = []
        caracteres_por_pagina = []

        for numero_pagina, pagina in enumerate(
            documento,
            start=1
        ):

            texto = pagina.get_text("text").strip()

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
            1
            for cantidad in caracteres_por_pagina
            if cantidad > 0
        )

        paginas_sin_texto = (
            numero_paginas - paginas_con_texto
        )

        # -------------------------------------------------
        # Diagnóstico
        # -------------------------------------------------

        st.subheader("Diagnóstico del documento")

        st.write(
            f"**Número de páginas:** {numero_paginas}"
        )

        st.write(
            f"**Caracteres extraídos:** {total_caracteres:,}"
        )

        st.write(
            f"**Páginas con texto:** {paginas_con_texto}"
        )

        st.write(
            f"**Páginas sin texto:** {paginas_sin_texto}"
        )

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

            # -------------------------------------------------
            # Búsqueda de CAS
            # -------------------------------------------------

            cas_encontrados = {}
            candidatos_invalidos = {}

            for pagina in paginas:

                validos, invalidos = extraer_cas(
                    pagina["texto"]
                )

                for cas in validos:

                    if cas not in cas_encontrados:
                        cas_encontrados[cas] = []

                    if pagina["pagina"] not in cas_encontrados[cas]:
                        cas_encontrados[cas].append(
                            pagina["pagina"]
                        )

                for cas in invalidos:

                    if cas not in candidatos_invalidos:
                        candidatos_invalidos[cas] = []

                    if pagina["pagina"] not in candidatos_invalidos[cas]:
                        candidatos_invalidos[cas].append(
                            pagina["pagina"]
                        )

# -------------------------------------------------
# Detección de zonas de composición
# -------------------------------------------------

bloques_composicion = detectar_bloques_composicion(
    paginas
)

st.subheader("Zonas candidatas de composición")

if bloques_composicion:

    st.success(
        f"Se encontraron "
        f"{len(bloques_composicion)} zona(s) candidata(s)."
    )

    for numero_bloque, bloque in enumerate(
        bloques_composicion,
        start=1
    ):

        with st.expander(
            f"Zona {numero_bloque} "
            f"— página {bloque['pagina']} "
            f"— {bloque['encabezado']}"
        ):

            st.text(
                "\n".join(bloque["lineas"])
            )

else:

    st.warning(
        "No se encontraron encabezados claros de "
        "composición o ingrediente activo."
    )
            
            st.subheader("Números CAS detectados")

            if cas_encontrados:

                st.success(
                    f"Se encontraron "
                    f"{len(cas_encontrados)} CAS válido(s)."
                )

                tabla_cas = []

                for cas, paginas_cas in cas_encontrados.items():

                    tabla_cas.append(
                        {
                            "CAS": cas,
                            "Página(s)": ", ".join(
                                str(p)
                                for p in paginas_cas
                            ),
                            "Validación": "Dígito de control válido"
                        }
                    )

                st.dataframe(
                    tabla_cas,
                    use_container_width=True,
                    hide_index=True
                )

            else:

                st.warning(
                    "No se encontraron números CAS válidos "
                    "en el documento."
                )

            # -------------------------------------------------
            # Candidatos con formato CAS pero inválidos
            # -------------------------------------------------

            if candidatos_invalidos:

                with st.expander(
                    "Ver candidatos con formato CAS "
                    "que no superaron la validación"
                ):

                    tabla_invalidos = []

                    for cas, paginas_cas in candidatos_invalidos.items():

                        tabla_invalidos.append(
                            {
                                "Candidato": cas,
                                "Página(s)": ", ".join(
                                    str(p)
                                    for p in paginas_cas
                                ),
                                "Validación": "Dígito de control inválido"
                            }
                        )

                    st.dataframe(
                        tabla_invalidos,
                        use_container_width=True,
                        hide_index=True
                    )

            # -------------------------------------------------
            # Texto extraído
            # -------------------------------------------------

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
