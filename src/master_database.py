from __future__ import annotations

import csv
from pathlib import Path

from .models import RestrictionMatch
from .text_utils import active_name_local_to_cas, names_equivalent


class MasterDatabase:
    def __init__(self, csv_path: str | Path):
        self.path = Path(csv_path)
        self.rows: list[dict[str, str]] = []
        self.by_cas: dict[str, list[dict[str, str]]] = {}
        with self.path.open("r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                cleaned = {key: (value or "").strip() for key, value in row.items()}
                self.rows.append(cleaned)
                cas = cleaned.get("cas", "")
                if cas:
                    self.by_cas.setdefault(cas, []).append(cleaned)

    def _confirm_active_from_names(self, master_name: str, active_names: list[dict] | None) -> tuple[bool, str]:
        for item in active_names or []:
            candidate = item.get("name", "")
            if names_equivalent(master_name, candidate):
                source = item.get("source_file", "documento")
                page = item.get("page")
                location = f"{source}, pág. {page}" if page else source
                return True, f"Nombre de ingrediente activo explícito '{candidate}' en {location}."
        return False, ""

    def _confirm_active_from_contexts(
        self,
        cas: str,
        active_names: list[dict] | None,
        occurrence_contexts: list[dict] | None,
    ) -> tuple[bool, str]:
        for active in active_names or []:
            active_name = active.get("name", "")
            for occurrence in occurrence_contexts or []:
                context = occurrence.get("context", "")
                if active_name_local_to_cas(active_name, cas, context):
                    source = occurrence.get("source_file", "documento")
                    page = occurrence.get("page")
                    location = f"{source}, pág. {page}" if page else source
                    return True, (
                        f"El nombre de ingrediente activo explícito '{active_name}' aparece "
                        f"en el contexto local del CAS en {location}."
                    )
        return False, ""

    def match_cas(
        self,
        cas: str,
        *,
        active_confirmed: bool,
        active_names: list[dict] | None = None,
        occurrence_contexts: list[dict] | None = None,
    ) -> list[RestrictionMatch]:
        matches: list[RestrictionMatch] = []
        for row in self.by_cas.get(cas, []):
            confirmed = active_confirmed
            evidence = "CAS ubicado en contexto explícito de ingrediente activo." if confirmed else ""
            if not confirmed and row.get("scope") in {"ACTIVE_INGREDIENT", "ROLE_CONFIRMATION_REQUIRED"}:
                confirmed, evidence = self._confirm_active_from_contexts(cas, active_names, occurrence_contexts)
                if not confirmed:
                    confirmed, evidence = self._confirm_active_from_names(row.get("ingredient", ""), active_names)

            matches.append(
                RestrictionMatch(
                    cas=cas,
                    source_list=row.get("source_list", ""),
                    action=row.get("action", ""),
                    scope=row.get("scope", ""),
                    ingredient=row.get("ingredient", ""),
                    usage=row.get("usage", ""),
                    criteria=row.get("criteria", ""),
                    source_code=row.get("source_code", ""),
                    source_version=row.get("source_version", ""),
                    source_date=row.get("source_date", ""),
                    active_confirmed=confirmed,
                    active_evidence=evidence,
                )
            )
        return matches

    @property
    def searchable_cas_count(self) -> int:
        return len(self.by_cas)
