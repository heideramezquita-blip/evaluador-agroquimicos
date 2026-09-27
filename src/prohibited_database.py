from __future__ import annotations

import csv
import re
from pathlib import Path

from .cas_utils import is_valid_cas
from .models import ProhibitedEntry
from .text_utils import match_key, normalize_text


VALID_SOURCE_LISTS = {"PROHIBITED", "OBSOLETE", "MITIGATE_RISK"}

GROUP_RULES = {
    "arsenico y sus compuestos": {
        "terms": ["arsenico", "arsenical", "arsenato", "arsenito", "arsonato", "arseniato"],
        "deterministic": False,
    },
    "borax sales de borato": {
        "terms": ["borax", "borato", "boratos", "borate"],
        "deterministic": True,
    },
    "dnoc y sus sales": {
        "terms": ["dnoc", "dinitro orto cresol", "dinitro-ortho-cresol"],
        "deterministic": True,
    },
    "formula en polvo dispersable que contiene una combinacion de benomilo 7 carbofurano 10 tiram 15": {
        "terms": ["benomilo", "carbofurano", "tiram"],
        "all_terms": True,
        "deterministic": False,
    },
    "sales e isomeros de glufosinato de amonio": {
        "terms": [
            "glufosinato de amonio",
            "glufosinato amonico",
            "ammonium glufosinate",
            "glufosinate ammonium",
        ],
        "deterministic": True,
    },
    "mercurio y sus compuestos": {
        "terms": ["mercurio", "mercurico", "mercuriosa", "mercurioso", "mercury"],
        "deterministic": False,
    },
    "aceites de parafina con un contenido de dmso 3": {
        "terms": ["aceite de parafina", "aceites de parafina", "paraffin oil", "paraffin oils"],
        "deterministic": False,
    },
    "compuestos de tributilestano": {
        "terms": ["tributilestano", "tributil estaño", "tributyltin"],
        "deterministic": True,
    },
}


def _aliases(name: str) -> tuple[str, ...]:
    values: list[str] = []
    seen: set[str] = set()

    for part in re.split(r";", name):
        candidates = [re.sub(r"\*+$", "", part).strip()]
        stripped = re.sub(r"\([^)]*\)", " ", candidates[0]).strip(" ,")
        if stripped and stripped != candidates[0]:
            candidates.append(stripped)

        for candidate in candidates:
            normalized = normalize_text(candidate)
            if candidate and len(normalized) >= 4 and normalized not in seen:
                seen.add(normalized)
                values.append(candidate)

    return tuple(values)


class ProhibitedDatabase:
    LIST_FILES = ("master_restrictions.csv", "obsolete.csv", "risk_mitigation.csv")

    def __init__(self, csv_path: str | Path):
        self.path = Path(csv_path)
        self.entries: list[ProhibitedEntry] = []
        self.by_cas: dict[str, list[ProhibitedEntry]] = {}
        self.specific: list[ProhibitedEntry] = []
        self.groups: list[ProhibitedEntry] = []
        self.prohibited: list[ProhibitedEntry] = []
        self.obsolete: list[ProhibitedEntry] = []
        self.mitigation: list[ProhibitedEntry] = []

        self._aliases_by_entry: dict[ProhibitedEntry, tuple[str, ...]] = {}
        self._alias_pairs_by_entry: dict[ProhibitedEntry, tuple[tuple[str, str], ...]] = {}
        self._group_rules_by_entry: dict[ProhibitedEntry, dict] = {}

        source_buckets = {
            "PROHIBITED": self.prohibited,
            "OBSOLETE": self.obsolete,
            "MITIGATE_RISK": self.mitigation,
        }

        for path in self._list_paths():
            with path.open(encoding="utf-8-sig", newline="") as source:
                for row in csv.DictReader(source):
                    source_list = (row.get("source_list") or "").strip()
                    if source_list not in VALID_SOURCE_LISTS:
                        continue

                    cas = (row.get("cas") or "").strip()
                    entry = ProhibitedEntry(
                        ingredient=(row.get("ingredient") or "").strip(),
                        cas=cas,
                        usage=(row.get("usage") or "").strip(),
                        criteria=(row.get("criteria") or "").strip(),
                        source_code=(row.get("source_code") or "").strip(),
                        source_version=(row.get("source_version") or "").strip(),
                        source_date=(row.get("source_date") or "").strip(),
                        is_group=not bool(cas),
                        source_list=source_list,
                        action=(row.get("action") or row.get("decision") or "").strip(),
                    )
                    self.entries.append(entry)
                    source_buckets[source_list].append(entry)

                    if cas:
                        if not is_valid_cas(cas):
                            raise ValueError(f"CAS inválido en {source_list}: {cas}")
                        self.specific.append(entry)
                        self.by_cas.setdefault(cas, []).append(entry)
                    else:
                        self.groups.append(entry)

        self._prepare_matching_metadata()

    def _list_paths(self) -> list[Path]:
        paths = [self.path]
        for name in self.LIST_FILES[1:]:
            candidate = self.path.parent / name
            if candidate.exists():
                paths.append(candidate)
        return paths

    def _prepare_matching_metadata(self) -> None:
        for entry in self.entries:
            aliases = _aliases(entry.ingredient)
            self._aliases_by_entry[entry] = aliases
            self._alias_pairs_by_entry[entry] = tuple(
                (alias, match_key(alias)) for alias in aliases
            )

        for entry in self.groups:
            if entry.source_list == "PROHIBITED":
                base_rule = GROUP_RULES.get(
                    match_key(entry.ingredient),
                    {"terms": self.aliases(entry), "deterministic": False},
                )
            else:
                base_rule = {"terms": self.aliases(entry), "deterministic": False}

            rule = dict(base_rule)
            rule["terms"] = tuple(rule["terms"])
            rule["term_keys"] = tuple(match_key(term) for term in rule["terms"])
            self._group_rules_by_entry[entry] = rule

    def aliases(self, entry: ProhibitedEntry) -> tuple[str, ...]:
        return self._aliases_by_entry[entry]

    def alias_pairs(self, entry: ProhibitedEntry) -> tuple[tuple[str, str], ...]:
        return self._alias_pairs_by_entry[entry]

    def group_rule(self, entry: ProhibitedEntry) -> dict:
        return self._group_rules_by_entry[entry]
