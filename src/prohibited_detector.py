from __future__ import annotations

from .context_classifier import REFERENCE_LIST, classify_context, has_reference_list_marker
from .models import EvidenceHit, PdfDocument
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
        "PRODUCT_IDENTITY": 2,
        "UNCERTAIN": 3,
        "INCIDENTAL": 4,
        "NEGATED": 5,
        "REFERENCE_TOXICOLOGY": 6,
        "DECOMPOSITION_COMBUSTION": 7,
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
    reference_list_document = has_reference_list_marker(
        "\n".join(page.text or "" for page in document.pages)
    )

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
                        (
                            REFERENCE_LIST
                            if reference_list_document
                            else classify_context(context, alias)
                        ),
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
                    (
                        REFERENCE_LIST
                        if reference_list_document
                        else classify_context(context, alias)
                    ),
                    strength,
                    "Coincidencia dirigida con un registro de grupo/familia de una lista normativa.",
                )
            )

    return hits


def detect_candidates(
    documents,
    cas_records,
    db,
) -> list[EvidenceHit]:
    """Run list-first screening against every readable document.

    CAS, normalized names/aliases and configured group rules are the primary
    evidence channels. Active-ingredient extraction is intentionally outside
    this decision path and is used only as auxiliary documentary information.
    """
    hits: list[EvidenceHit] = []
    reference_list_files = {
        document.file_name
        for document in documents
        if has_reference_list_marker(
            "\n".join(page.text or "" for page in document.pages)
        )
    }

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
                        (
                            REFERENCE_LIST
                            if occurrence.source_file in reference_list_files
                            else classify_context(occurrence.context, record.cas)
                        ),
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
