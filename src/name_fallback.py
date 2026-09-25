from __future__ import annotations

import re

from .models import PdfDocument
from .text_utils import normalize_text


ACTIVE_LABELS = (
    "ingrediente activo",
    "ingredientes activos",
    "active ingredient",
    "active ingredients",
)

BOUNDARIES = (
    "nombre quimico",
    "nombre iupac",
    "concentracion",
    "formulacion",
    "ingrediente aditivo",
    "ingredientes aditivos",
    "ingrediente inerte",
    "ingredientes inertes",
    "grupo quimico",
    "formula",
    "registro",
    "categoria toxicologica",
    "modo de accion",
    "mecanismo de accion",
    "cultivo",
    "compatibilidad",
    "fitotoxicidad",
    "almacenamiento",
    "seccion",
    "section",
    "caracteristicas",
    "propiedades",
    "componentes",
    "componente",
)

REJECT_STARTS = (
    "compatible",
    "velocidad de mezcla",
    "rapida",
    "adherencia",
    "calle ",
    "region ",
    "periodo de ",
    "agregar ",
    "establezca ",
    "verifique ",
    "considerando ",
    "a.: no aplica",
    "no aplica",
    "cl50",
    "dl50",
    "ce50",
    "ec50",
    "erc50",
    "noec",
)


def _looks_like_concentration(value: str) -> bool:
    n = normalize_text(value)
    return bool(
        re.search(r"\b\d+(?:[.,]\d+)?\s*(?:%|g\s*/\s*l|g\s*/\s*kg|mg\s*/\s*l|ufc\s*/|x\s*10)", n, flags=re.I)
    )


def _strip_concentration_suffix(value: str) -> str:
    if "/" in value:
        left, right = value.rsplit("/", 1)
        right_norm = normalize_text(right)
        if _looks_like_concentration(right) or (re.search(r"\d", right_norm) and re.search(r"(?:g\s*/?\s*l|g\s*/?\s*kg|%|ufc)", right_norm)):
            value = left
    value = re.sub(
        r"\s+\d+(?:[.,]\d+)?(?:\s*\+\s*\d+(?:[.,]\d+)?)*\s*(?:%|g\s*/\s*l|g\s*/\s*kg|mg\s*/\s*l|ufc\s*/.*)$",
        "",
        value,
        flags=re.I,
    )
    return value.strip(" .;:-/")


def _clean_line(value: str) -> list[str]:
    value = re.sub(r"^[a-zA-Z]\s*[.)-]\s*", "", value.strip())
    value = re.sub(r"[.·…]{4,}.*$", "", value).strip()
    value = _strip_concentration_suffix(value)

    if ":" in value:
        left, right = value.split(":", 1)
        if 2 <= len(left.strip()) <= 80 and len(right.strip()) >= 12:
            value = left.strip()

    if normalize_text(value).endswith("equivalente a"):
        return []

    parts = [p.strip(" .;:-/") for p in re.split(r"\s*\+\s*", value) if p.strip(" .;:-/")]
    result: list[str] = []
    for part in parts:
        n = normalize_text(part)
        if not part or len(part) > 100:
            continue
        if any(n.startswith(boundary) for boundary in BOUNDARIES):
            continue
        if any(n.startswith(prefix) for prefix in REJECT_STARTS):
            continue
        if n in {"a", "b", "c", "d", "g/kg", "g/l"}:
            continue
        if _looks_like_concentration(part) and sum(ch.isalpha() for ch in part) < 8:
            continue
        part = re.sub(r"\s*\([a-z]\)\s*$", "", part, flags=re.I).strip()
        if sum(ch.isalpha() for ch in part) < 2:
            continue
        if len(part.split()) > 8:
            continue
        result.append(part)
    return result


def _merge_split_taxon(first: str, second: str) -> str | None:
    n1 = normalize_text(first)
    if n1.endswith("subsp") or n1.endswith("subsp."):
        second_clean = _strip_concentration_suffix(second)
        second_clean = second_clean.split("/", 1)[0].strip()
        if second_clean and len(second_clean.split()) <= 3:
            return f"{first.rstrip()} {second_clean}".strip()
    return None


def _add_candidate(results: list[dict], seen: list[str], candidate: str, *, source_file: str, page: int, evidence: str) -> None:
    key = normalize_text(candidate)
    if not key:
        return

    for idx, existing_key in enumerate(list(seen)):
        if key == existing_key:
            return
        if existing_key.startswith(key + " "):
            return
        if key.startswith(existing_key + " "):
            seen[idx] = key
            results[idx] = {
                "name": candidate,
                "source_file": source_file,
                "page": page,
                "evidence": evidence,
            }
            return

    seen.append(key)
    results.append({
        "name": candidate,
        "source_file": source_file,
        "page": page,
        "evidence": evidence,
    })


def extract_explicit_active_names(documents: list[PdfDocument]) -> list[dict]:
    """Conservative fallback: only names explicitly labeled as active ingredients."""
    results: list[dict] = []
    seen: list[str] = []

    for document in documents:
        if not document.processable:
            continue
        for page in document.pages:
            lines = [line.strip() for line in page.text.splitlines() if line.strip()]
            for idx, line in enumerate(lines):
                nline = normalize_text(line).rstrip(" :.-")
                label = next((lbl for lbl in ACTIVE_LABELS if nline == lbl or nline.startswith(lbl + ":")), None)
                if not label:
                    continue

                plural = "ingredientes" in label or "ingredients" in label
                raw_candidates: list[str] = []

                if ":" in line:
                    inline = line.split(":", 1)[1].strip()
                    if inline:
                        raw_candidates.append(inline)

                if not raw_candidates:
                    following = lines[idx + 1 : idx + 6]
                    j = 0
                    while j < len(following):
                        next_line = following[j]
                        nn = normalize_text(next_line)
                        if any(nn.startswith(boundary) for boundary in BOUNDARIES):
                            break
                        if any(nn.startswith(prefix) for prefix in REJECT_STARTS):
                            break
                        if _looks_like_concentration(next_line) and not any(ch.isalpha() for ch in next_line.split("/")[0]):
                            break

                        if j + 1 < len(following):
                            merged = _merge_split_taxon(next_line, following[j + 1])
                            if merged:
                                raw_candidates.append(merged)
                                j += 2
                                if not plural:
                                    break
                                continue

                        raw_candidates.append(next_line)
                        j += 1
                        if not plural:
                            break
                        if len(raw_candidates) >= 3:
                            break

                cleaned: list[str] = []
                for raw in raw_candidates:
                    cleaned.extend(_clean_line(raw))

                for candidate in cleaned:
                    _add_candidate(
                        results,
                        seen,
                        candidate,
                        source_file=document.file_name,
                        page=page.page,
                        evidence=line,
                    )

    return results
