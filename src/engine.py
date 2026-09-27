from __future__ import annotations

from pathlib import Path

from .cas_extractor import extract_document_cas, merge_cas_records
from .cas_utils import parse_manual_cas
from .context_classifier import ACTIVE, COMPOSITION, classify_context, has_active_marker
from .models import CasOccurrence, CasRecord
from .pdf_reader import read_pdf
from .prohibited_database import ProhibitedDatabase
from .prohibited_detector import detect_candidates
from .rules import evaluate_prohibited


DEFAULT_MASTER_PATH = Path(__file__).resolve().parents[1] / "data" / "master_restrictions.csv"


def _identity_basis(documents, records) -> list[str]:
    """Describe whether there was enough chemical identity to support a clean no-match."""
    basis: list[str] = []

    contextual_document_cas = any(
        occurrence.source == "document"
        and classify_context(occurrence.context, record.cas) in {ACTIVE, COMPOSITION}
        for record in records
        for occurrence in record.occurrences
    )
    if contextual_document_cas:
        basis.append("CAS válido en contexto de ingrediente activo/composición")

    # A bare composition heading is not enough to support a clean no-match:
    # several real SDS files in the benchmark expose "3. COMPOSICIÓN" while
    # the actual component table is image-based or missing from extracted
    # text. Require either a contextual validated CAS (above) or an explicit
    # active-ingredient label.
    explicit_active_section = any(
        has_active_marker(page.text or "")
        for document in documents
        if document.processable
        for page in document.pages
    )
    if explicit_active_section:
        basis.append("referencia explícita a ingrediente activo")

    manual_cas = any(
        occurrence.source == "manual"
        for record in records
        for occurrence in record.occurrences
    )
    if manual_cas:
        basis.append("CAS manual válido")

    return basis


def _manual_records(valid_cas: list[str], active_confirmed: bool) -> list[CasRecord]:
    role = "active_explicit" if active_confirmed else "unknown"
    return [
        CasRecord(
            cas,
            [
                CasOccurrence(
                    cas,
                    "Entrada manual",
                    None,
                    "manual",
                    role,
                    "CAS introducido manualmente.",
                )
            ],
        )
        for cas in valid_cas
    ]


def analyze(files, *, manual_cas_text="", manual_active_confirmed=False, master_path=None):
    master_path = Path(master_path) if master_path is not None else DEFAULT_MASTER_PATH
    database = ProhibitedDatabase(master_path)

    documents = []
    record_groups = []
    invalid_candidates = []
    warnings = []
    read_failures = 0

    for file_name, payload in files:
        try:
            document = read_pdf(payload, file_name)
        except Exception as exc:
            read_failures += 1
            warnings.append(f"No fue posible leer {file_name}: {exc}")
            continue

        documents.append(document)
        warnings.extend(document.warnings)
        records, invalid = extract_document_cas(document)
        record_groups.append(records)
        invalid_candidates.extend(invalid)

    manual_valid, manual_invalid = parse_manual_cas(manual_cas_text)
    record_groups.append(_manual_records(manual_valid, manual_active_confirmed))
    records = merge_cas_records(record_groups)

    hits = detect_candidates(documents, records, database)
    if manual_active_confirmed:
        for hit in hits:
            if hit.channel == "CAS" and hit.source_file == "Entrada manual":
                hit.context_class = ACTIVE

    unprocessables = read_failures + sum(
        not document.processable for document in documents
    )
    if manual_valid and not documents:
        warnings.append(
            "La entrada manual de CAS solo evalúa coincidencias por CAS específico; "
            "no excluye registros normativos definidos sin CAS."
        )

    identity_basis = _identity_basis(documents, records)
    evaluation = evaluate_prohibited(
        records,
        hits,
        warnings,
        unprocessables,
        identity_basis=identity_basis,
    )

    return {
        "evaluation": evaluation,
        "documents": documents,
        "invalid_candidates": invalid_candidates,
        "manual_valid": manual_valid,
        "manual_invalid": manual_invalid,
        "all_hits": hits,
        "identity_basis": identity_basis,
        "prohibited_specific_count": sum(bool(entry.cas) for entry in database.prohibited),
        "prohibited_group_count": sum(not bool(entry.cas) for entry in database.prohibited),
        "obsolete_count": len(database.obsolete),
        "mitigation_count": len(database.mitigation),
    }
