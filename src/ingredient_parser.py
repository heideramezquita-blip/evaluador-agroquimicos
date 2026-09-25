import unicodedata


ENCABEZADOS_COMPOSICION = [
    "ingrediente activo",
    "ingredientes activos",
    "composicion",
    "composicion garantizada",
    "composicion quimica",
    "active ingredient",
    "active ingredients",
    "composition",
]


def normalizar_texto(texto):
    """
    Normaliza texto para comparar encabezados:
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


def detectar_bloques_composicion(paginas, lineas_despues=12):
    """
    Busca encabezados relacionados con composición o ingrediente activo
    y devuelve las líneas cercanas como zonas candidatas.

    No decide todavía cuál es el ingrediente activo.
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

        posiciones = []

        for indice, linea in enumerate(lineas):

            linea_normalizada = normalizar_texto(linea)

            if any(
                encabezado in linea_normalizada
                for encabezado in ENCABEZADOS_COMPOSICION
            ):
                posiciones.append(indice)

        # Evitar mostrar bloques prácticamente duplicados
        ultimo_fin = -1

        for indice in posiciones:

            inicio = indice
            fin = min(
                len(lineas),
                indice + lineas_despues + 1
            )

            if inicio < ultimo_fin:
                continue

            bloques.append(
                {
                    "pagina": numero_pagina,
                    "encabezado": lineas[indice],
                    "lineas": lineas[inicio:fin],
                }
            )

            ultimo_fin = fin

    return bloques
