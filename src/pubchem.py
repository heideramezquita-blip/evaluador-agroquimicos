from __future__ import annotations

import re
from urllib.parse import quote

import requests

from .cas_utils import is_valid_cas


PUBCHEM_BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
CAS_IN_TEXT = re.compile(r"(?<!\d)(\d{2,7}-\d{2}-\d)(?!\d)")


def _valid_cas_strings(obj: object) -> list[str]:
    found: list[str] = []
    if isinstance(obj, dict):
        for value in obj.values():
            for cas in _valid_cas_strings(value):
                if cas not in found:
                    found.append(cas)
    elif isinstance(obj, list):
        for value in obj:
            for cas in _valid_cas_strings(value):
                if cas not in found:
                    found.append(cas)
    elif isinstance(obj, str):
        for cas in CAS_IN_TEXT.findall(obj):
            if is_valid_cas(cas) and cas not in found:
                found.append(cas)
    return found


def consultar_pubchem(nombre: str, timeout: int = 10) -> dict:
    nombre = (nombre or "").strip()
    result = {
        "nombre_consultado": nombre,
        "estado": "error",
        "cid": None,
        "cas": None,
        "cas_candidatos": [],
        "mensaje": "",
    }
    if not nombre:
        result["mensaje"] = "Nombre vacío."
        return result

    headers = {"User-Agent": "evaluador-agroquimicos/0.2"}
    encoded = quote(nombre, safe="")

    try:
        r = requests.get(f"{PUBCHEM_BASE}/compound/name/{encoded}/cids/JSON", headers=headers, timeout=timeout)
        if r.status_code == 404:
            result.update(estado="no_encontrado", mensaje="PubChem no encontró el nombre.")
            return result
        r.raise_for_status()
        cids = list(dict.fromkeys(r.json().get("IdentifierList", {}).get("CID", [])))
        if not cids:
            result.update(estado="no_encontrado", mensaje="PubChem no devolvió CID.")
            return result
        if len(cids) != 1:
            result.update(estado="ambiguo", mensaje=f"PubChem devolvió {len(cids)} CID posibles.")
            return result

        cid = cids[0]
        result["cid"] = cid

        r2 = requests.get(
            f"{PUBCHEM_BASE}/compound/cid/{cid}/identifiers/JSON?identifier_type=CAS",
            headers=headers,
            timeout=timeout,
        )
        candidates: list[str] = []
        if r2.ok:
            candidates = _valid_cas_strings(r2.json())

        if not candidates:
            r3 = requests.get(f"{PUBCHEM_BASE}/compound/cid/{cid}/synonyms/JSON", headers=headers, timeout=timeout)
            if r3.ok:
                candidates = _valid_cas_strings(r3.json())

        result["cas_candidatos"] = candidates
        if len(candidates) == 1:
            result.update(
                estado="identificado",
                cas=candidates[0],
                mensaje="Nombre resuelto a un CAS único mediante PubChem.",
            )
        elif not candidates:
            result.update(estado="sin_cas", mensaje="PubChem identificó el compuesto, pero no devolvió un CAS único utilizable.")
        else:
            result.update(estado="varios_cas", mensaje="PubChem devolvió varios CAS válidos; se requiere revisión manual.")
        return result
    except (requests.RequestException, ValueError) as error:
        result.update(estado="error", mensaje=f"No fue posible consultar PubChem: {error}")
        return result
