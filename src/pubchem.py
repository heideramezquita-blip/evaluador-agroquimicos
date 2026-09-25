import re
from urllib.parse import quote

import requests


PUBCHEM_BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"

PATRON_CAS = re.compile(
    r"(?<!\d)(\d{2,7}-\d{2}-\d)(?!\d)"
)


def validar_cas(cas):
    """
    Valida matemáticamente el dígito de control CAS.
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

    return suma % 10 == int(digito_control)


def extraer_cas_de_json(objeto):
    """
    Recorre una respuesta JSON de PubChem y extrae
    cadenas con estructura CAS válida.
    """

    encontrados = set()

    if isinstance(objeto, dict):

        for valor in objeto.values():
            encontrados.update(
                extraer_cas_de_json(valor)
            )

    elif isinstance(objeto, list):

        for valor in objeto:
            encontrados.update(
                extraer_cas_de_json(valor)
            )

    elif isinstance(objeto, str):

        for cas in PATRON_CAS.findall(objeto):

            if validar_cas(cas):
                encontrados.add(cas)

    return encontrados


def consultar_pubchem(nombre):
    """
    Consulta un ingrediente por nombre en PubChem.

    Estados posibles:
    - identificado
    - no_encontrado
    - ambiguo
    - sin_cas
    - varios_cas
    - error
    """

    nombre = nombre.strip()

    resultado = {
        "nombre_consultado": nombre,
        "estado": None,
        "cid": None,
        "cas": None,
        "cas_candidatos": [],
        "mensaje": None,
    }

    if not nombre:

        resultado["estado"] = "error"
        resultado["mensaje"] = (
            "El nombre del ingrediente está vacío."
        )

        return resultado

    nombre_url = quote(
        nombre,
        safe=""
    )

    cabeceras = {
        "User-Agent": (
            "evaluador-agroquimicos/0.1 "
            "(Streamlit prototype)"
        )
    }

    # -------------------------------------------------
    # 1. Buscar CID por nombre
    # -------------------------------------------------

    url_cid = (
        f"{PUBCHEM_BASE}/compound/name/"
        f"{nombre_url}/cids/JSON"
    )

    try:

        respuesta = requests.get(
            url_cid,
            headers=cabeceras,
            timeout=10
        )

        if respuesta.status_code == 404:

            resultado["estado"] = "no_encontrado"
            resultado["mensaje"] = (
                "PubChem no encontró una coincidencia "
                "para este nombre."
            )

            return resultado

        respuesta.raise_for_status()

        datos = respuesta.json()

        cids = (
            datos
            .get("IdentifierList", {})
            .get("CID", [])
        )

        # Eliminar duplicados conservando orden
        cids = list(dict.fromkeys(cids))

        if not cids:

            resultado["estado"] = "no_encontrado"
            resultado["mensaje"] = (
                "PubChem no devolvió ningún CID."
            )

            return resultado

        if len(cids) > 1:

            resultado["estado"] = "ambiguo"
            resultado["mensaje"] = (
                f"PubChem devolvió {len(cids)} "
                "compuestos posibles para este nombre."
            )

            return resultado

        cid = cids[0]

        resultado["cid"] = cid

        # -------------------------------------------------
        # 2. Obtener identificadores CAS para ese CID
        # -------------------------------------------------

        url_cas = (
            f"{PUBCHEM_BASE}/compound/cid/"
            f"{cid}/identifiers/JSON"
            f"?identifier_type=CAS"
        )

        respuesta_cas = requests.get(
            url_cas,
            headers=cabeceras,
            timeout=10
        )

        if respuesta_cas.status_code == 404:

            resultado["estado"] = "sin_cas"
            resultado["mensaje"] = (
                "Se encontró el compuesto en PubChem, "
                "pero no se obtuvo un identificador CAS."
            )

            return resultado

        respuesta_cas.raise_for_status()

        datos_cas = respuesta_cas.json()

        cas_encontrados = sorted(
            extraer_cas_de_json(datos_cas)
        )

        resultado["cas_candidatos"] = cas_encontrados

        if len(cas_encontrados) == 0:

            resultado["estado"] = "sin_cas"
            resultado["mensaje"] = (
                "PubChem identificó el compuesto, "
                "pero no devolvió un CAS utilizable."
            )

            return resultado

        if len(cas_encontrados) > 1:

            resultado["estado"] = "varios_cas"
            resultado["mensaje"] = (
                "PubChem devolvió varios CAS para "
                "el mismo compuesto. Requiere revisión manual."
            )

            return resultado

        resultado["estado"] = "identificado"
        resultado["cas"] = cas_encontrados[0]

        resultado["mensaje"] = (
            "Ingrediente y CAS identificados en PubChem."
        )

        return resultado

    except requests.RequestException as error:

        resultado["estado"] = "error"
        resultado["mensaje"] = (
            f"No fue posible consultar PubChem: {error}"
        )

        return resultado

    except ValueError:

        resultado["estado"] = "error"
        resultado["mensaje"] = (
            "PubChem devolvió una respuesta que no pudo "
            "interpretarse como JSON."
        )

        return resultado
