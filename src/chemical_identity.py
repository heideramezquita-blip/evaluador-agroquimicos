from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from .text_utils import match_key


@dataclass(frozen=True)
class ChemicalAlias:
    substance_id: str
    canonical_cas: str
    alias: str
    language: str
    alias_type: str
    source: str
    confidence: str
    enabled: bool


@dataclass(frozen=True)
class ChemicalSubstance:
    substance_id: str
    canonical_name: str
    canonical_cas: str
    parent_substance_id: str
    chemical_form: str
    source: str


class ChemicalIdentityRegistry:
    """Local, deterministic chemical identity registry.

    The application never calls PubChem at evaluation time. Registry CSV files
    are generated deliberately during maintenance and shipped with the repo.
    """

    def __init__(self, data_dir: str | Path):
        self.data_dir = Path(data_dir)
        self.substances_by_cas: dict[str, ChemicalSubstance] = {}
        self.substances_by_id: dict[str, ChemicalSubstance] = {}
        self.aliases_by_cas: dict[str, list[ChemicalAlias]] = {}
        self.aliases_by_id: dict[str, list[ChemicalAlias]] = {}
        self._load_substances()
        self._load_aliases()

    def _load_substances(self) -> None:
        path = self.data_dir / "chemical_substances.csv"
        if not path.exists():
            return
        with path.open(encoding="utf-8-sig", newline="") as source:
            for row in csv.DictReader(source):
                item = ChemicalSubstance(
                    substance_id=(row.get("substance_id") or "").strip(),
                    canonical_name=(row.get("canonical_name") or "").strip(),
                    canonical_cas=(row.get("canonical_cas") or "").strip(),
                    parent_substance_id=(row.get("parent_substance_id") or "").strip(),
                    chemical_form=(row.get("chemical_form") or "").strip(),
                    source=(row.get("source") or "").strip(),
                )
                if not item.substance_id:
                    continue
                self.substances_by_id[item.substance_id] = item
                if item.canonical_cas:
                    self.substances_by_cas[item.canonical_cas] = item

    def _load_aliases(self) -> None:
        path = self.data_dir / "chemical_aliases.csv"
        if not path.exists():
            return
        with path.open(encoding="utf-8-sig", newline="") as source:
            for row in csv.DictReader(source):
                alias = (row.get("alias") or "").strip()
                substance_id = (row.get("substance_id") or "").strip()
                if not alias or not substance_id:
                    continue
                item = ChemicalAlias(
                    substance_id=substance_id,
                    canonical_cas=(row.get("canonical_cas") or "").strip(),
                    alias=alias,
                    language=(row.get("language") or "und").strip(),
                    alias_type=(row.get("alias_type") or "synonym").strip(),
                    source=(row.get("source") or "").strip(),
                    confidence=(row.get("confidence") or "").strip(),
                    enabled=(row.get("enabled") or "").strip().lower()
                    in {"1", "true", "yes", "si", "sí"},
                )
                self.aliases_by_id.setdefault(substance_id, []).append(item)
                if item.canonical_cas:
                    self.aliases_by_cas.setdefault(item.canonical_cas, []).append(item)

    def substance_for_cas(self, cas: str) -> ChemicalSubstance | None:
        return self.substances_by_cas.get(cas)

    def enabled_aliases_for_cas(self, cas: str) -> tuple[ChemicalAlias, ...]:
        return tuple(
            alias
            for alias in self.aliases_by_cas.get(cas, [])
            if alias.enabled and match_key(alias.alias)
        )

    @property
    def substance_count(self) -> int:
        return len(self.substances_by_id)

    @property
    def alias_count(self) -> int:
        return sum(len(values) for values in self.aliases_by_id.values())

    @property
    def enabled_alias_count(self) -> int:
        return sum(
            alias.enabled
            for values in self.aliases_by_id.values()
            for alias in values
        )
