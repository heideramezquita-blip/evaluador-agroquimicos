import unicodedata


ENCABEZADOS_EXACTOS = {
    "ingrediente activo",
    "ingredientes activos",
    "composicion",
    "composicion garantizada",
    "composicion quimica",
    "active ingredient",
    "active ingredients",
    "composition",
}


def normalizar_texto(texto):
    """
    Normaliza texto para comparación:
    - minúsculas
    - sin tildes
    - espacios normalizados
    """

    texto = texto.lower().strip()

    texto = unicodedata.normalize("NFD", texto)

    texto = "".join(
        caracter
        for caracter in texto
        if unicodedata.category(caracter) != "Mn"
    )

    return " ".join(texto.split())


def limpiar_final_encabezado(texto):
    """
    Elimina signos finales habituales de encabezados.
    """

    return texto.rstrip(" :.-")


def es_encabezado_composicion(linea):
    """
    Determina si una línea es realmente un encabezado
    relacionado con composición.

    Evita falsos positivos como:
    - descomposición
    - productos de descomposición
    """

    linea_normalizada = normalizar_texto(linea)
    linea_limpia = limpiar_final_encabezado(
        linea_normalizada
    )

    # Encabezados exactos
    if linea_limpia in ENCABEZADOS_EXACTOS:
        return True

    # Encabezados que contienen información en la misma línea
    if linea_limpia.startswith("ingrediente activo:"):
        return True

    if linea_limpia.startswith("ingredientes activos:"):
        return True

    if linea_limpia.startswith("active ingredient:"):
        return True

    if linea_limpia.startswith("active ingredients:"):
        return True

    # Sección 3 típica de una SDS
    if (
        linea_limpia.startswith("seccion 3")
        and "composicion" in linea_limpia
        and "ingrediente" in linea_limpia
    ):
        return True

    return False


def encontrar_fin_seccion_3(lineas, indice_inicio):
    """
    Si estamos en la Sección 3 de una SDS,
    intenta capturar hasta el comienzo de la Sección 4.
    """

    for indice in range(
        indice_inicio + 1,
        len(lineas)
    ):

        linea_normalizada = normalizar_texto(
            lineas[indice]
        )

        if linea_normalizada.startswith("seccion 4"):
            return indice

    # Límite de seguridad si no encuentra Sección 4
    return min(
        len(lineas),
        indice_inicio + 50
    )


def detectar_bloques_composicion(
    paginas,
    lineas_despues=20
):
    """
    Detecta zonas candidatas de composición.

    Para Sección 3 de SDS:
    captura hasta Sección 4.

    Para fichas técnicas:
    captura un bloque local alrededor del encabezado.
    """

    bloques = []

    for pagina in paginas:

        numero_pagina = pagina["pagina"]
        texto = pagina["texto"]

        lineas = [
            linea.strip()
            for linea in texto.splitlines()
            if linea.strip()
        ]

        rangos_usados = []

        for indice, linea in enumerate(lineas):

            if not es_encabezado_composicion(linea):
                continue

            linea_normalizada = normalizar_texto(
                linea
            )

            # Caso SDS — Sección 3
            if (
                linea_normalizada.startswith("seccion 3")
                and "composicion" in linea_normalizada
            ):

                inicio = indice

                fin = encontrar_fin_seccion_3(
                    lineas,
                    indice
                )

            # Caso ficha técnica / encabezado local
            else:

                inicio = indice

                fin = min(
                    len(lineas),
                    indice + lineas_despues + 1
                )

            # Evitar bloques duplicados o solapados
            solapado = any(
                inicio >= rango_inicio
                and inicio < rango_fin
                for rango_inicio, rango_fin
                in rangos_usados
            )

            if solapado:
                continue

            bloques.append(
                {
                    "pagina": numero_pagina,
                    "encabezado": lineas[indice],
                    "lineas": lineas[inicio:fin],
                }
            )

            rangos_usados.append(
                (inicio, fin)
            )

    return bloques
