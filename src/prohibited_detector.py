from __future__ import annotations

from .context_classifier import ACTIVE, classify_context
from .models import ActiveIngredientEvidence, EvidenceHit, PdfDocument
from .text_utils import match_key, phrase_present


def _line_context(text: str, needle: str, radius_lines: int = 8) -> str:
    """Return the most informative local context for a matched substance name.

    A product name can repeat in headers/footers before the chemically useful
    occurrence appears (for example, "Producto: Paraquat..." above
    "Ingredientes Activos: Paraquat 200 g/L"). Returning the first occurrence
    therefore downgraded explicit active-ingredient evidence to UNCERTAIN.

    Evaluate every local occurrence and prefer direct identity evidence while
    keeping incidental/negated/reference mentions lower priority.
    """
    # PDF text extraction often inserts many empty layout lines between a
    # heading and its value. Work on semantic (non-empty) lines so the context
    # radius measures content rather than page-layout whitespace.
    lines = [line for line in text.splitlines() if line.strip()]
    needle_key = match_key(needle)
    tokens = [token for token in needle_key.split() if len(token) >= 4]
    candidates = []

    priority = {
        "ACTIVE": 0,
        "COMPOSITION": 1,
        "UNCERTAIN": 2,
        "INCIDENTAL": 3,
        "NEGATED": 4,
        "REFERENCE_TOXICOLOGY": 5,
        "DECOMPOSITION_COMBUSTION": 6,
    }

    for index, line in enumerate(lines):
        line_key = match_key(line)
        if not needle_key or not (
            needle_key in line_key or (tokens and tokens[0] in line_key)
        ):
            continue

        context = " | ".join(
            item.strip()
            for item in lines[
                max(0, index - radius_lines) : min(
                    len(lines), index + radius_lines + 1
                )
            ]
            if item.strip()
        )
        if not phrase_present(context, needle):
            continue

        context_class = classify_context(context, needle)
        candidates.append((priority.get(context_class, 9), index, context))

    if candidates:
        return min(candidates, key=lambda item: (item[0], item[1]))[2]

    return text[:700]


def _key_present(padded_page_key: str, phrase_key: str) -> bool:
    return bool(phrase_key) and f" {phrase_key} " in padded_page_key


def _name_hits(document: PdfDocument, db) -> list[EvidenceHit]:
    hits: list[EvidenceHit] = []

    for page in document.pages:
        if not page.text:
            continue

        # Name matching previously normalized the entire page once per alias.
        # The matching semantics are unchanged; only the normalized page key is
        # now reused across all entries on the page.
        padded_page_key = f" {match_key(page.text)} "

        for entry in db.specific:
            for alias, alias_key in db.alias_pairs(entry):
                if not _key_present(padded_page_key, alias_key):
                    continue

                context = _line_context(page.text, alias)
                hits.append(
                    EvidenceHit(
                        entry,
                        "NAME",
                        alias,
                        document.file_name,
                        page.page,
                        context,
                        classify_context(context, alias),
                        "exact_name",
                        "Coincidencia nominal exacta/normalizada con una lista normativa.",
                    )
                )
                break

        for entry in db.groups:
            rule = db.group_rule(entry)
            terms = rule["terms"]
            term_keys = rule["term_keys"]

            if rule.get("all_terms"):
                if not all(
                    _key_present(padded_page_key, term_key)
                    for term_key in term_keys
                ):
                    continue
                alias = " + ".join(terms)
                context = page.text[:1200]
            else:
                alias = next(
                    (
                        term
                        for term, term_key in zip(terms, term_keys)
                        if _key_present(padded_page_key, term_key)
                    ),
                    None,
                )
                if not alias:
                    continue
                context = _line_context(page.text, alias)

            strength = (
                "group_deterministic"
                if rule.get("deterministic")
                else "group_candidate"
            )
            hits.append(
                EvidenceHit(
                    entry,
                    "GROUP_NAME",
                    alias,
                    document.file_name,
                    page.page,
                    context,
                    classify_context(context, alias),
                    strength,
                    "Coincidencia dirigida con un registro de grupo/familia de una lista normativa.",
                )
            )

    return hits


def _active_identity_hits(
    active_ingredients: list[ActiveIngredientEvidence],
    db,
) -> list[EvidenceHit]:
    """Match explicitly extracted active ingredients against specific list entries.

    This path is deliberately stricter than free-text page matching: the name
    must equal one of the normalized aliases of a specific entry. It converts
    documentary identity already established by the dedicated extractor into
    decisive list evidence without requiring a CAS to be present in the PDF.
    """
    hits: list[EvidenceHit] = []

    for item in active_ingredients:
        item_key = match_key(item.name)

        for entry in db.specific:
            cas_match = bool(item.cas and entry.cas and item.cas == entry.cas)
            matched_alias = next(
                (
                    alias
                    for alias, alias_key in db.alias_pairs(entry)
                    if item_key and alias_key == item_key
                ),
                None,
            )
            if not cas_match and not matched_alias:
                continue

            strength = "validated_cas" if cas_match else "exact_name"
            detail = (
                "Identidad química del producto/ingrediente confirmada documentalmente "
                "y coincidente por CAS validado con una lista de referencia."
                if cas_match
                else
                "Ingrediente activo identificado explícitamente por el documento "
                "y coincidente de forma exacta/normalizada con una lista de referencia."
            )
            hits.append(
                EvidenceHit(
                    entry,
                    "ACTIVE_IDENTITY",
                    item.name,
                    item.source_file,
                    item.page,
                    item.context or item.name,
                    "ACTIVE",
                    strength,
                    detail,
                )
            )

    return hits


def _phrase_relation(left_key: str, right_key: str) -> bool:
    """Return whether two normalized chemical names have a whole-phrase relation."""
    if not left_key or not right_key:
        return False
    left = f" {left_key} "
    right = f" {right_key} "
    return left in right or right in left


def _entry_supported_by_active_identity(
    entry,
    active_ingredients: list[ActiveIngredientEvidence],
    db,
) -> bool:
    """Return whether a list entry is supported by confirmed product identity.

    Once the document explicitly establishes one or more active ingredients,
    incidental chemistry elsewhere in the PDFs must not become product
    identity merely because it matches a regulatory/reference list.
    """
    for item in active_ingredients:
        if item.cas and entry.cas and item.cas == entry.cas:
            return True

        item_key = match_key(item.name)
        if not item_key:
            continue

        if entry.cas:
            if any(
                _phrase_relation(alias_key, item_key)
                for _, alias_key in db.alias_pairs(entry)
            ):
                return True
            continue

        rule = db.group_rule(entry)
        term_keys = [key for key in rule.get("term_keys", ()) if key]
        if rule.get("all_terms"):
            if term_keys and all(
                _phrase_relation(term_key, item_key)
                for term_key in term_keys
            ):
                return True
        elif any(
            _phrase_relation(term_key, item_key)
            for term_key in term_keys
        ):
            return True

    return False


def _gate_hits_to_active_identity(
    hits: list[EvidenceHit],
    active_ingredients: list[ActiveIngredientEvidence],
    db,
) -> list[EvidenceHit]:
    """Discard unrelated free-text/CAS hits once active identity is confirmed.

    The dedicated active-ingredient extractor is the identity gate. A mention
    such as "mezclas en tanque con ... paraquat" can remain useful traceability
    text, but it must not drive the regulatory result for a product explicitly
    identified as glyphosate. Manual CAS input remains independent.
    """
    if not active_ingredients:
        return hits

    gated: list[EvidenceHit] = []
    for hit in hits:
        if hit.channel == "ACTIVE_IDENTITY" or hit.source_file == "Entrada manual":
            gated.append(hit)
            continue

        if _entry_supported_by_active_identity(hit.entry, active_ingredients, db):
            gated.append(hit)
            continue

        # Preserve genuinely active group/family evidence. Non-deterministic
        # group rules can still require human review when the group wording is
        # itself located in the explicit active-ingredient context.
        if hit.entry.is_group and hit.context_class == ACTIVE:
            gated.append(hit)

    return gated


def detect_candidates(
    documents,
    cas_records,
    db,
    active_ingredients: list[ActiveIngredientEvidence] | None = None,
) -> list[EvidenceHit]:
    """Run list-first screening against every readable document.

    CAS, normalized names/aliases and configured group rules are the primary
    evidence channels. active_ingredients is retained for call compatibility
    and presentation elsewhere, but it does not create, suppress or gate
    regulatory matches.
    """
    del active_ingredients
    hits: list[EvidenceHit] = []

    for record in cas_records:
        for entry in db.by_cas.get(record.cas, []):
            for occurrence in record.occurrences:
                hits.append(
                    EvidenceHit(
                        entry,
                        "CAS",
                        record.cas,
                        occurrence.source_file,
                        occurrence.page,
                        occurrence.context,
                        classify_context(occurrence.context, record.cas),
                        "validated_cas",
                        "CAS válido por checksum e incluido en una lista normativa.",
                    )
                )

    for document in documents:
        hits.extend(_name_hits(document, db))

    unique: list[EvidenceHit] = []
    seen = set()
    for hit in hits:
        key = (
            hit.entry.ingredient,
            hit.channel,
            hit.matched_value,
            hit.source_file,
            hit.page,
            hit.context_class,
        )
        if key not in seen:
            seen.add(key)
            unique.append(hit)

    return unique
