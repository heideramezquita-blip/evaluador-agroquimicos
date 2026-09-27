from __future__ import annotations

from .context_classifier import classify_context
from .models import EvidenceHit, PdfDocument
from .text_utils import match_key, phrase_present


def _line_context(text: str, needle: str, radius_lines: int = 8) -> str:
    lines = text.splitlines()
    needle_key = match_key(needle)
    tokens = [token for token in needle_key.split() if len(token) >= 4]

    for index, line in enumerate(lines):
        line_key = match_key(line)
        if needle_key and (
            needle_key in line_key or (tokens and tokens[0] in line_key)
        ):
            context = " | ".join(
                item.strip()
                for item in lines[
                    max(0, index - radius_lines) : min(
                        len(lines), index + radius_lines + 1
                    )
                ]
                if item.strip()
            )
            if phrase_present(context, needle):
                return context

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


def detect_candidates(documents, cas_records, db) -> list[EvidenceHit]:
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
