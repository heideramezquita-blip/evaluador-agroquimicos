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

import re


PATRON_CAS_LINEA = re.compile(
    r"^\s*(\d{2,7})\s*[-‐-‒–—−]\s*(\d{2})\s*[-‐-‒–—−]\s*(\d)\s*$"
)


def normalizar_cas_linea(linea):
    """
    Si una línea contiene únicamente un CAS,
    devuelve el CAS normalizado con guiones ASCII.

    Si no corresponde a un CAS completo, devuelve None.
    """

    coincidencia = PATRON_CAS_LINEA.match(
        linea.strip()
    )

    if not coincidencia:
        return None

    return (
        f"{coincidencia.group(1)}-"
        f"{coincidencia.group(2)}-"
        f"{coincidencia.group(3)}"
    )


def parece_concentracion(linea):
    """
    Reconoce formatos habituales de concentración.

    Ejemplos:
    >= 10 - < 20
    >= 0,0003 - < 0,0015
    15 %
    600 g/kg
    """

    texto = linea.strip().lower()

    patrones = [
        r"^[<>=~≤≥\s]*\d+(?:[.,]\d+)?"
        r"(?:\s*[-–]\s*[<>=~≤≥\s]*\d+(?:[.,]\d+)?)?"
        r"\s*%?\s*(?:w/w|p/p|v/v|p/v)?$",

        r"^\d+(?:[.,]\d+)?\s*"
        r"(?:g/kg|g/l|mg/l|mg/kg|%|ppm|ppb)$",
    ]

    return any(
        re.match(patron, texto, re.IGNORECASE)
        for patron in patrones
    )


def extraer_componentes_sds(bloque):
    """
    Extrae componentes de una Sección 3 de SDS.

    Estructura esperada después de los encabezados:

    nombre químico
    [continuación opcional del nombre]
    CAS
    concentración

    Devuelve una lista con:
    - nombre
    - CAS
    - concentración
    - página
    """

    lineas = bloque["lineas"]

    # -------------------------------------------------
    # Localizar el encabezado de concentración
    # -------------------------------------------------

    indice_inicio = None

    for indice, linea in enumerate(lineas):

        linea_normalizada = normalizar_texto(
            linea
        )

        if (
            "concentracion" in linea_normalizada
            and (
                "%" in linea
                or "w/w" in linea_normalizada
                or "p/p" in linea_normalizada
            )
        ):
            indice_inicio = indice + 1
            break

    if indice_inicio is None:
        return []

    datos = lineas[indice_inicio:]

    componentes = []
    nombre_acumulado = []

    indice = 0

    while indice < len(datos):

        linea = datos[indice].strip()

        cas = normalizar_cas_linea(linea)

        # Todavía estamos acumulando el nombre
        if cas is None:

            if linea:
                nombre_acumulado.append(linea)

            indice += 1
            continue

        # Encontramos CAS
        nombre = " ".join(nombre_acumulado).strip()

        nombre_acumulado = []

        concentracion = None

        # Buscar la primera línea siguiente
        # que tenga apariencia de concentración
        siguiente = indice + 1

        while siguiente < len(datos):

            candidata = datos[siguiente].strip()

            if parece_concentracion(candidata):
                concentracion = candidata
                break

            # Si encontramos otro CAS antes,
            # no asignamos concentración.
            if normalizar_cas_linea(candidata):
                break

            siguiente += 1

        componentes.append(
            {
                "nombre": nombre,
                "cas": cas,
                "concentracion": concentracion,
                "pagina": bloque["pagina"],
            }
        )

        # Continuamos después de la concentración
        if concentracion is not None:
            indice = siguiente + 1
        else:
            indice += 1

    return componentes
def extraer_ingredientes_activos_explicitos(bloques):
    """
    Busca declaraciones explícitas de ingrediente activo.

    Solo devuelve sustancias cuando el documento utiliza
    expresamente etiquetas como:
    - Ingrediente activo
    - Ingredientes activos
    - Active ingredient
    - Active ingredients

    No convierte automáticamente componentes de una SDS
    en ingredientes activos.
    """

    resultados = []

    etiquetas = {
        "ingrediente activo",
        "ingredientes activos",
        "active ingredient",
        "active ingredients",
    }

    for bloque in bloques:

        lineas = bloque["lineas"]

        for indice, linea in enumerate(lineas):

            linea_normalizada = normalizar_texto(linea)
            linea_limpia = limpiar_final_encabezado(
                linea_normalizada
            )

            # ---------------------------------------------
            # ¿Es una etiqueta explícita?
            # ---------------------------------------------

            es_etiqueta = (
                linea_limpia in etiquetas
                or any(
                    linea_normalizada.startswith(
                        etiqueta + ":"
                    )
                    for etiqueta in etiquetas
                )
            )

            if not es_etiqueta:
                continue

            nombre = None
            concentracion = None

            # ---------------------------------------------
            # Caso: Ingrediente activo: Azoxystrobin
            # ---------------------------------------------

            if ":" in linea:

                valor_misma_linea = (
                    linea.split(":", 1)[1].strip()
                )

                if valor_misma_linea:
                    nombre = valor_misma_linea

            # ---------------------------------------------
            # Caso:
            # Ingrediente activo:
            # Metsulfuron Metil
            # ---------------------------------------------

            if nombre is None:

                siguiente = indice + 1

                while siguiente < len(lineas):

                    candidata = lineas[
                        siguiente
                    ].strip()
if candidata:

    # Algunas fichas usan:
    # Nombre común: nombre químico/IUPAC
    #
    # Ejemplo:
    # Chlorantraniliprole:3-bromo-4'-chloro-...

    if ":" in candidata:

        posible_nombre = candidata.split(
            ":",
            1
        )[0].strip()

        if posible_nombre:
            nombre = posible_nombre

    else:
        nombre = candidata

    break

                    siguiente += 1

            if not nombre:
                continue

            # ---------------------------------------------
            # Buscar concentración cerca del ingrediente
            # ---------------------------------------------

            limite_busqueda = min(
                len(lineas),
                indice + 20
            )

            for posicion in range(
                indice + 1,
                limite_busqueda
            ):

                candidata = lineas[
                    posicion
                ].strip()

                candidata_normalizada = (
                    normalizar_texto(candidata)
                )

                # Ejemplo:
                # Concentración:
                # 600 g/kg
                if candidata_normalizada.startswith(
                    "concentracion"
                ):

                    # Valor en la misma línea
                    if ":" in candidata:

                        valor = candidata.split(
                            ":",
                            1
                        )[1].strip()

                        if valor:
                            concentracion = valor
                            break

                    # Valor en la siguiente línea
                    if posicion + 1 < len(lineas):

                        siguiente_valor = lineas[
                            posicion + 1
                        ].strip()

                        if siguiente_valor:
                            concentracion = (
                                siguiente_valor
                            )
                            break

            resultados.append(
                {
                    "nombre": nombre,
                    "concentracion": concentracion,
                    "pagina": bloque["pagina"],
                    "evidencia": linea,
                }
            )

    # -------------------------------------------------
    # Eliminar duplicados
    # -------------------------------------------------

    unicos = {}

    for resultado in resultados:

        clave = normalizar_texto(
            resultado["nombre"]
        )

        if clave not in unicos:

            unicos[clave] = resultado

        else:

            # Si una aparición tiene concentración
            # y la anterior no, conservar la más completa.
            if (
                not unicos[clave]["concentracion"]
                and resultado["concentracion"]
            ):
                unicos[clave] = resultado

    return list(unicos.values())
