from __future__ import annotations

from pathlib import Path

from .cas_extractor import extract_document_cas, merge_cas_records
from .cas_utils import parse_manual_cas
from .context_classifier import ACTIVE, COMPOSITION, classify_context
from .models import CasOccurrence, CasRecord
from .pdf_reader import read_pdf
from .prohibited_database import ProhibitedDatabase
from .prohibited_detector import detect_candidates
from .rules import evaluate_prohibited
from .text_utils import normalize_text


IDENTITY_MARKERS = (
    "ingrediente activo",
    "ingredientes activos",
    "principio activo",
    "principios activos",
    "active ingredient",
    "active ingredients",
    "composicion garantizada",
    "composicion/informacion sobre los ingredientes",
    "composicion informacion sobre los ingredientes",
    "composicion/informacion sobre los componentes",
    "composicion informacion sobre los componentes",
)


def _identity_basis(documents, records):
    """Describe whether there was enough chemical identity to support a clean no-match."""
    basis = []

    contextual_document_cas = any(
        occurrence.source == "document"
        and classify_context(occurrence.context, record.cas) in {ACTIVE, COMPOSITION}
        for record in records
        for occurrence in record.occurrences
    )
    if contextual_document_cas:
        basis.append("CAS válido en contexto de ingrediente activo/composición")

    explicit_identity_section = any(
        any(marker in normalize_text(page.text or "") for marker in IDENTITY_MARKERS)
        for document in documents
        if document.processable
        for page in document.pages
    )
    if explicit_identity_section:
        basis.append("referencia explícita a ingrediente activo/composición")

    manual_cas = any(
        occurrence.source == "manual"
        for record in records
        for occurrence in record.occurrences
    )
    if manual_cas:
        basis.append("CAS manual válido")

    return basis


def analyze(files, *, manual_cas_text="", manual_active_confirmed=False, master_path=None):
    if master_path is None:
        master_path = Path(__file__).resolve().parents[1] / "data" / "master_restrictions.csv"

    db = ProhibitedDatabase(master_path)
    documents = []
    groups = []
    invalid = []
    warnings = []

    for name, payload in files:
        try:
            doc = read_pdf(payload, name)
        except Exception as exc:
            warnings.append(f"No fue posible leer {name}: {exc}")
            continue
        documents.append(doc)
        warnings.extend(doc.warnings)
        recs, bad = extract_document_cas(doc)
        groups.append(recs)
        invalid.extend(bad)

    manual_valid, manual_invalid = parse_manual_cas(manual_cas_text)
    manual_records = []
    for cas in manual_valid:
        role = "active_explicit" if manual_active_confirmed else "unknown"
        manual_records.append(
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
        )

    groups.append(manual_records)
    records = merge_cas_records(groups)
    hits = detect_candidates(documents, records, db)

    for hit in hits:
        if (
            hit.channel == "CAS"
            and hit.source_file == "Entrada manual"
            and manual_active_confirmed
        ):
            hit.context_class = "ACTIVE"

    unprocessables = sum(not document.processable for document in documents)
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
        "invalid_candidates": invalid,
        "manual_valid": manual_valid,
        "manual_invalid": manual_invalid,
        "all_hits": hits,
        "identity_basis": identity_basis,
        "prohibited_specific_count": sum(bool(entry.cas) for entry in db.prohibited),
        "prohibited_group_count": sum(not bool(entry.cas) for entry in db.prohibited),
        "obsolete_count": len(db.obsolete),
        "mitigation_count": len(db.mitigation),
    }
