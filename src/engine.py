from __future__ import annotations

from pathlib import Path

from .cas_extractor import extract_document_cas, merge_cas_records
from .cas_utils import parse_manual_cas
from .master_database import MasterDatabase
from .models import CasOccurrence, CasRecord
from .name_fallback import extract_explicit_active_names
from .pdf_reader import read_pdf
from .pubchem import consultar_pubchem
from .rules import apply_rules


def _record_from_manual(cas: str, active_confirmed: bool) -> CasRecord:
    return CasRecord(
        cas=cas,
        occurrences=[
            CasOccurrence(
                cas=cas,
                source_file="Entrada manual",
                page=None,
                source="manual",
                role="active_explicit" if active_confirmed else "unknown",
                context="CAS introducido manualmente por el usuario.",
            )
        ],
    )


def _record_from_pubchem(cas: str, item: dict, cid: int | str | None) -> CasRecord:
    return CasRecord(
        cas=cas,
        occurrences=[
            CasOccurrence(
                cas=cas,
                source_file=item["source_file"],
                page=item["page"],
                source="pubchem",
                role="active_explicit",
                context=f"Ingrediente activo declarado: {item['name']}",
                note=f"PubChem CID: {cid}" if cid else "CAS resuelto por PubChem",
            )
        ],
    )


def analyze(
    files: list[tuple[str, bytes]],
    *,
    manual_cas_text: str = "",
    manual_active_confirmed: bool = False,
    master_path: str | Path,
    enable_name_fallback: bool = True,
) -> dict:
    documents = []
    record_groups: list[list[CasRecord]] = []
    invalid_candidates: list[dict] = []
    warnings: list[str] = []

    for file_name, pdf_bytes in files:
        try:
            document = read_pdf(pdf_bytes, file_name)
            documents.append(document)
            warnings.extend(f"{file_name}: {w}" for w in document.warnings)
            records, invalid = extract_document_cas(document)
            record_groups.append(records)
            invalid_candidates.extend(invalid)
        except Exception as error:
            warnings.append(f"{file_name}: no fue posible procesar el PDF ({error}).")

    automatic_records = merge_cas_records(record_groups)

    active_names = extract_explicit_active_names(documents) if documents else []
    fallback_attempts: list[dict] = []

    if not automatic_records and enable_name_fallback and documents:
        for item in active_names:
            result = consultar_pubchem(item["name"])
            fallback_attempts.append({**item, **result})
            if result.get("estado") == "identificado" and result.get("cas"):
                record_groups.append([_record_from_pubchem(result["cas"], item, result.get("cid"))])

    manual_valid, manual_invalid = parse_manual_cas(manual_cas_text)
    if manual_invalid:
        warnings.append("CAS manual(es) con dígito de control inválido: " + ", ".join(manual_invalid))
    if manual_valid:
        record_groups.append([_record_from_manual(cas, manual_active_confirmed) for cas in manual_valid])

    records = merge_cas_records(record_groups)
    database = MasterDatabase(master_path)
    matches = []
    for record in records:
        matches.extend(
            database.match_cas(
                record.cas,
                active_confirmed=record.active_confirmed,
                active_names=active_names,
                occurrence_contexts=[
                    {
                        "source_file": occurrence.source_file,
                        "page": occurrence.page,
                        "context": occurrence.context,
                    }
                    for occurrence in record.occurrences
                ],
            )
        )

    evaluation = apply_rules(records, matches, warnings)
    return {
        "evaluation": evaluation,
        "documents": documents,
        "invalid_candidates": invalid_candidates,
        "manual_valid": manual_valid,
        "manual_invalid": manual_invalid,
        "fallback_attempts": fallback_attempts,
        "active_names": active_names,
        "database_searchable_cas": database.searchable_cas_count,
    }
