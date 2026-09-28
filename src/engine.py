from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from .active_ingredient_extractor import extract_active_ingredients
from .cas_extractor import extract_document_cas, merge_cas_records
from .composition_extractor import extract_composition_components
from .cas_utils import parse_manual_cas
from .context_classifier import ACTIVE, COMPOSITION, classify_context
from .models import (
    ActiveIngredientEvidence,
    CasOccurrence,
    CasRecord,
    CompositionComponentEvidence,
    PdfDocument,
)
from .pdf_reader import read_pdf
from .prohibited_database import ProhibitedDatabase
from .prohibited_detector import detect_candidates
from .rules import evaluate_prohibited, relevant_supporting_hits
from .text_utils import match_key


DEFAULT_MASTER_PATH = Path(__file__).resolve().parents[1] / "data" / "master_restrictions.csv"


def _database_signature(master_path: Path) -> tuple[tuple[str, int, int], ...]:
    """Return a cheap cache key that changes when any local list changes."""
    paths = [master_path]
    paths.extend(
        master_path.parent / name
        for name in ProhibitedDatabase.LIST_FILES[1:]
        if (master_path.parent / name).exists()
    )
    return tuple(
        (str(path.resolve()), path.stat().st_mtime_ns, path.stat().st_size)
        for path in paths
    )


@lru_cache(maxsize=4)
def _cached_database(
    master_path: str,
    signature: tuple[tuple[str, int, int], ...],
) -> ProhibitedDatabase:
    # The signature only participates in the cache key. It invalidates the
    # cached database when any local CSV changes.
    del signature
    return ProhibitedDatabase(master_path)


def _load_database(master_path: Path) -> ProhibitedDatabase:
    resolved = master_path.resolve()
    return _cached_database(str(resolved), _database_signature(resolved))


def _screening_identity(
    records: list[CasRecord],
    active_ingredients: list[ActiveIngredientEvidence],
    composition_components: list[CompositionComponentEvidence] | None = None,
) -> dict:
    """Return the exact chemical identity that was usable for screening.

    This is deliberately narrower than all detected chemistry: document CAS
    values are included only when their local context identifies ingredient
    active/composition. Incidental CAS values remain traceability data but are
    not presented as the basis of a clean no-match.
    """
    document_cas: list[str] = []
    manual_cas: list[str] = []

    for record in records:
        if any(
            occurrence.source == "document"
            and classify_context(occurrence.context, record.cas)
            in {ACTIVE, COMPOSITION}
            for occurrence in record.occurrences
        ):
            document_cas.append(record.cas)

        if any(
            occurrence.source == "manual"
            for occurrence in record.occurrences
        ):
            manual_cas.append(record.cas)

    active = []
    seen_names: set[str] = set()
    for item in active_ingredients:
        key = match_key(item.name)
        if not key or key in seen_names:
            continue
        seen_names.add(key)
        active.append(
            {
                "name": item.name,
                "cas": item.cas,
                "source_file": item.source_file,
                "page": item.page,
            }
        )

    composition = []
    seen_components: set[tuple[str, str]] = set()
    for item in composition_components or []:
        key = (match_key(item.name), item.cas)
        if not key[0] or key in seen_components:
            continue
        seen_components.add(key)
        composition.append(
            {
                "name": item.name,
                "cas": item.cas,
                "source_file": item.source_file,
                "page": item.page,
            }
        )
        if item.cas:
            document_cas.append(item.cas)

    return {
        "active_ingredients": active,
        "composition_components": composition,
        "document_cas": list(dict.fromkeys(document_cas)),
        "manual_cas": list(dict.fromkeys(manual_cas)),
    }


def _identity_basis_from_screening(screening_identity: dict) -> list[str]:
    basis: list[str] = []
    if screening_identity["document_cas"]:
        basis.append("CAS válido en contexto de ingrediente activo/composición")
    if screening_identity["active_ingredients"]:
        basis.append("referencia explícita a ingrediente activo")
    if screening_identity.get("composition_components"):
        basis.append("componentes de composición estructurados")
    if screening_identity["manual_cas"]:
        basis.append("CAS manual válido")
    return basis


def _identity_basis(
    documents: list[PdfDocument],
    records: list[CasRecord],
    active_ingredients: list[ActiveIngredientEvidence] | None = None,
) -> list[str]:
    """Describe whether there was enough chemical identity to support a clean no-match."""
    if active_ingredients is None:
        active_ingredients = [
            item
            for document in documents
            if document.processable
            for item in extract_active_ingredients(document)
        ]
    return _identity_basis_from_screening(
        _screening_identity(records, active_ingredients)
    )


def _enrich_active_ingredients(
    active_ingredients: list[ActiveIngredientEvidence],
    composition_components: list[CompositionComponentEvidence],
) -> list[ActiveIngredientEvidence]:
    """Fill missing active-ingredient metadata from an exact composition row.

    This never promotes a composition component to active ingredient. It only
    enriches an identity that another documentary path already established.
    """
    by_name: dict[str, CompositionComponentEvidence] = {}
    for component in composition_components:
        key = match_key(component.name)
        if key:
            by_name[key] = component

    by_cas = {
        component.cas: component
        for component in composition_components
        if component.cas
    }

    for item in active_ingredients:
        component = by_name.get(match_key(item.name))
        if component is None and item.cas:
            component = by_cas.get(item.cas)
        if component is None:
            continue
        if not item.cas and component.cas:
            item.cas = component.cas
        if not item.concentration and component.concentration:
            item.concentration = component.concentration

    return active_ingredients


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
    database = _load_database(master_path)

    documents = []
    record_groups = []
    invalid_candidates = []
    warnings = []
    active_ingredients = []
    composition_components = []
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
        if document.processable:
            active_ingredients.extend(extract_active_ingredients(document))
            composition_components.extend(extract_composition_components(document))

    active_ingredients = _enrich_active_ingredients(
        active_ingredients,
        composition_components,
    )

    manual_valid, manual_invalid = parse_manual_cas(manual_cas_text)
    record_groups.append(_manual_records(manual_valid, manual_active_confirmed))
    records = merge_cas_records(record_groups)

    hits = detect_candidates(documents, records, database, active_ingredients)
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

    screening_identity = _screening_identity(
        records,
        active_ingredients,
        composition_components,
    )
    identity_basis = _identity_basis_from_screening(screening_identity)
    evaluation = evaluate_prohibited(
        records,
        hits,
        warnings,
        unprocessables,
        identity_basis=identity_basis,
    )
    display_hits = relevant_supporting_hits(hits) or evaluation.hits

    return {
        "evaluation": evaluation,
        "documents": documents,
        "invalid_candidates": invalid_candidates,
        "manual_valid": manual_valid,
        "manual_invalid": manual_invalid,
        "all_hits": hits,
        "display_hits": display_hits,
        "identity_basis": identity_basis,
        "screening_identity": screening_identity,
        "active_ingredients": active_ingredients,
        "composition_components": composition_components,
        "prohibited_specific_count": sum(bool(entry.cas) for entry in database.prohibited),
        "prohibited_group_count": sum(not bool(entry.cas) for entry in database.prohibited),
        "obsolete_count": len(database.obsolete),
        "mitigation_count": len(database.mitigation),
    }
