from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from .active_ingredient_extractor import extract_active_ingredients
from .cas_extractor import extract_document_cas, merge_cas_records
from .composition_extractor import extract_composition_components
from .cas_utils import parse_manual_cas
from .context_classifier import ACTIVE, COMPOSITION, PRODUCT_IDENTITY, REFERENCE_LIST, classify_context
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
            in {ACTIVE, COMPOSITION, PRODUCT_IDENTITY}
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


def _targeted_screening_basis(
    documents: list[PdfDocument],
    manual_valid: list[str],
) -> list[str]:
    """Describe the material that was actually searched against local lists."""
    basis: list[str] = []
    processable = sum(document.processable for document in documents)
    if processable:
        basis.append(
            f"{processable} documento(s) con texto extraíble"
        )
    if manual_valid:
        basis.append(
            f"{len(manual_valid)} CAS manual(es) válido(s)"
        )
    return basis


def _detected_identities(hits) -> list[dict]:
    """Collapse raw hit channels into one inventory row per list identity.

    A substance found by both CAS and name remains one detected identity.
    Multiple CAS rows for the same named list identity are grouped together.
    This inventory is intentionally independent of whether the context is
    strong enough to drive the regulatory decision.
    """
    grouped: dict[tuple[str, str], dict] = {}

    for hit in hits:
        key = (hit.entry.source_list, hit.entry.ingredient)
        item = grouped.setdefault(
            key,
            {
                "source_list": hit.entry.source_list,
                "ingredient": hit.entry.ingredient,
                "cas_values": set(),
                "files": set(),
                "pages": set(),
                "contexts": set(),
                "channels": set(),
            },
        )
        if hit.entry.cas:
            item["cas_values"].add(hit.entry.cas)
        if hit.source_file:
            item["files"].add(hit.source_file)
        if hit.page:
            item["pages"].add(hit.page)
        if hit.context_class:
            item["contexts"].add(hit.context_class)
        if hit.channel:
            item["channels"].add(hit.channel)

    result = []
    for item in grouped.values():
        result.append(
            {
                "source_list": item["source_list"],
                "ingredient": item["ingredient"],
                "cas_values": sorted(item["cas_values"]),
                "files": sorted(item["files"]),
                "pages": sorted(item["pages"]),
                "contexts": sorted(item["contexts"]),
                "channels": sorted(item["channels"]),
            }
        )

    return sorted(
        result,
        key=lambda item: (
            item["source_list"],
            match_key(item["ingredient"]),
        ),
    )


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


def _sanitize_active_ingredients(
    active_ingredients: list[ActiveIngredientEvidence],
    documents: list[PdfDocument],
) -> list[ActiveIngredientEvidence]:
    """Apply a final documentary sanity check before screening/UI.

    The extractor intentionally supports many heterogeneous PDF layouts. This
    guard prevents two high-cost failure classes from leaking into the result:
    structural table headers presented as chemical names, and biological-target
    rows from recommendation tables presented as additional active ingredients.
    """
    document_by_name = {document.file_name: document for document in documents}
    strong_by_file: dict[str, set[str]] = {}

    for item in active_ingredients:
        key = match_key(item.name)
        if key and (item.concentration or item.cas):
            strong_by_file.setdefault(item.source_file, set()).add(key)

    structural_names = {
        "nombre",
        "identificador",
        "identificador del producto",
        "porcentaje",
        "concentracion",
        "cas",
        "numero cas",
        "densidad",
        "ph",
        "tension superficial",
        "solubilidad",
        "viscosidad",
        "apariencia",
        "color",
        "olor",
    }
    use_cues = (
        "recomendaciones de uso",
        "objetivo biologico",
        "blanco biologico",
        "malezas a controlar",
        "dosis",
    )

    cleaned: list[ActiveIngredientEvidence] = []
    for item in active_ingredients:
        key = match_key(item.name)
        if not key or key in structural_names:
            continue

        strong_keys = strong_by_file.get(item.source_file, set())
        if not item.concentration and not item.cas and strong_keys and key not in strong_keys:
            document = document_by_name.get(item.source_file)
            page_text = ""
            if document is not None:
                for page in document.pages:
                    if page.page == item.page:
                        page_text = page.text or ""
                        break
            page_key = match_key(page_text)
            if any(cue in page_key for cue in use_cues):
                continue

        cleaned.append(item)

    return cleaned


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
    active_ingredients = _sanitize_active_ingredients(
        active_ingredients,
        documents,
    )

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

    screening_identity = _screening_identity(
        records,
        active_ingredients,
        composition_components,
    )
    identity_basis = _identity_basis_from_screening(screening_identity)
    screening_basis = _targeted_screening_basis(documents, manual_valid)
    detected_identities = _detected_identities(hits)
    targeted_screening = {
        "documents_received": len(files),
        "documents_processable": sum(
            document.processable for document in documents
        ),
        "entries_screened": len(database.entries),
        "matched_records": len({
            (hit.entry.source_list, hit.entry.ingredient, hit.entry.cas)
            for hit in hits
        }),
        "matched_identities": len(detected_identities),
        "manual_cas_valid": len(manual_valid),
    }
    evaluation = evaluate_prohibited(
        records,
        hits,
        warnings,
        unprocessables,
        identity_basis=identity_basis,
        screening_basis=screening_basis,
    )
    reference_list_only = bool(hits) and all(
        hit.context_class == REFERENCE_LIST for hit in hits
    )
    display_hits = (
        []
        if reference_list_only
        else (relevant_supporting_hits(hits) or evaluation.hits)
    )

    return {
        "evaluation": evaluation,
        "documents": documents,
        "invalid_candidates": invalid_candidates,
        "manual_valid": manual_valid,
        "manual_invalid": manual_invalid,
        "all_hits": hits,
        "display_hits": display_hits,
        "identity_basis": identity_basis,
        "screening_basis": screening_basis,
        "targeted_screening": targeted_screening,
        "detected_identities": detected_identities,
        "screening_identity": screening_identity,
        "active_ingredients": active_ingredients,
        "composition_components": composition_components,
        "prohibited_specific_count": sum(bool(entry.cas) for entry in database.prohibited),
        "prohibited_group_count": sum(not bool(entry.cas) for entry in database.prohibited),
        "obsolete_count": len(database.obsolete),
        "mitigation_count": len(database.mitigation),
    }
