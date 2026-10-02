from __future__ import annotations

import csv
import json
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
LIST_FILES = ("master_restrictions.csv", "obsolete.csv", "risk_mitigation.csv")
SUBSTANCES_PATH = DATA / "chemical_substances.csv"
ALIASES_PATH = DATA / "chemical_aliases.csv"

PUBCHEM = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{identifier}/{endpoint}/JSON"
USER_AGENT = "evaluador-agroquimicos/chemical-identity-maintenance"
# PubChem is used only here; runtime screening remains offline and deterministic.

# Explicit structural relationships used only as identity metadata. They do
# not propagate or alter any regulatory decision.
CURATED_RELATIONSHIPS = {
    "1910-42-5": ("4685-14-7", "salt"),       # paraquat dichloride -> paraquat
    "959-98-8": ("115-29-7", "isomer"),       # alpha-endosulfan -> endosulfan
    "33213-65-9": ("115-29-7", "isomer"),     # beta-endosulfan -> endosulfan
    "319-84-6": ("608-73-1", "isomer"),       # alpha-HCH -> mixed HCH
    "319-85-7": ("608-73-1", "isomer"),       # beta-HCH -> mixed HCH
    "58-89-9": ("608-73-1", "isomer"),        # gamma-HCH/lindane -> mixed HCH
}


def _fold(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(c for c in value if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def _clean_local_name(value: str) -> str:
    value = re.sub(r"\[[0-9]+\]", "", value or "")
    return re.sub(r"\*+$", "", value).strip(" ;,")


def _local_aliases(name: str) -> list[str]:
    aliases = []
    seen = set()
    for part in re.split(r";", name or ""):
        alias = _clean_local_name(part)
        key = _fold(alias)
        if len(key) >= 4 and key not in seen:
            seen.add(key)
            aliases.append(alias)
    return aliases


def _substance_id(cas: str, fallback_name: str) -> str:
    if cas:
        return "CAS_" + cas.replace("-", "_")
    slug = re.sub(r"[^A-Z0-9]+", "_", _fold(fallback_name).upper()).strip("_")
    return "GROUP_" + slug[:80]


def _fetch_json(identifier: str, endpoint: str, retries: int = 3) -> dict:
    url = PUBCHEM.format(
        identifier=urllib.parse.quote(identifier, safe=""),
        endpoint=endpoint,
    )
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return {}
            if attempt + 1 == retries:
                raise
        except (urllib.error.URLError, TimeoutError):
            if attempt + 1 == retries:
                raise
        time.sleep(0.5 * (attempt + 1))
    return {}


def _pubchem_properties(cas: str) -> tuple[str, str]:
    data = _fetch_json(cas, "property/Title,IUPACName")
    rows = data.get("PropertyTable", {}).get("Properties", [])
    if not rows:
        return "", ""
    row = rows[0]
    return (row.get("Title") or "").strip(), (row.get("IUPACName") or "").strip()


def _safe_enabled_alias(alias: str, *, alias_type: str) -> bool:
    key = _fold(alias)
    if len(key) < 4:
        return False
    if alias_type in {"regulatory_name", "pubchem_title"}:
        return True
    if alias_type == "iupac":
        return len(alias) <= 180
    return False


def _add_alias(rows: list[dict], seen: set[tuple[str, str]], **row) -> None:
    key = (row["substance_id"], _fold(row["alias"]))
    if not key[1] or key in seen:
        return
    seen.add(key)
    rows.append(row)


def load_regulatory_rows() -> list[dict]:
    rows = []
    for file_name in LIST_FILES:
        path = DATA / file_name
        with path.open(encoding="utf-8-sig", newline="") as source:
            for row in csv.DictReader(source):
                ingredient = (row.get("ingredient") or "").strip()
                cas = (row.get("cas") or "").strip()
                if ingredient:
                    rows.append({"ingredient": ingredient, "cas": cas, "file": file_name})
    return rows


def build_registry() -> tuple[list[dict], list[dict], list[dict]]:
    regulatory = load_regulatory_rows()
    substances: list[dict] = []
    aliases: list[dict] = []
    failures: list[dict] = []
    alias_seen: set[tuple[str, str]] = set()

    # CAS is the safest cross-list identity key. Group records without CAS keep
    # their own group identity and continue to use explicit group rules.
    by_cas: dict[str, list[dict]] = defaultdict(list)
    groups: list[dict] = []
    for row in regulatory:
        if row["cas"]:
            by_cas[row["cas"]].append(row)
        else:
            groups.append(row)

    for cas, rows in sorted(by_cas.items()):
        local_names = list(dict.fromkeys(_clean_local_name(r["ingredient"]) for r in rows))
        substance_id = _substance_id(cas, local_names[0])
        title = ""
        iupac = ""
        try:
            title, iupac = _pubchem_properties(cas)
        except Exception as exc:
            failures.append({"cas": cas, "error": repr(exc)})

        canonical_name = title or local_names[0]
        parent_cas, chemical_form = CURATED_RELATIONSHIPS.get(cas, ("", ""))
        substances.append(
            {
                "substance_id": substance_id,
                "canonical_name": canonical_name,
                "canonical_cas": cas,
                "parent_substance_id": _substance_id(parent_cas, "") if parent_cas else "",
                "chemical_form": chemical_form,
                "source": "PubChem title + local regulatory lists" if title else "local regulatory lists",
            }
        )

        for name in local_names:
            for alias in _local_aliases(name):
                _add_alias(
                    aliases,
                    alias_seen,
                    substance_id=substance_id,
                    canonical_cas=cas,
                    alias=alias,
                    language="es",
                    alias_type="regulatory_name",
                    source="Rainforest Alliance local list",
                    confidence="high",
                    enabled="true",
                )

        if title:
            _add_alias(
                aliases,
                alias_seen,
                substance_id=substance_id,
                canonical_cas=cas,
                alias=title,
                language="en_or_international",
                alias_type="pubchem_title",
                source="PubChem PUG REST",
                confidence="high",
                enabled="true" if _safe_enabled_alias(title, alias_type="pubchem_title") else "false",
            )

        if iupac:
            _add_alias(
                aliases,
                alias_seen,
                substance_id=substance_id,
                canonical_cas=cas,
                alias=iupac,
                language="international",
                alias_type="iupac",
                source="PubChem PUG REST",
                confidence="high",
                enabled="true" if _safe_enabled_alias(iupac, alias_type="iupac") else "false",
            )

        time.sleep(0.04)

    for row in groups:
        name = _clean_local_name(row["ingredient"])
        substance_id = _substance_id("", name)
        if any(item["substance_id"] == substance_id for item in substances):
            continue
        substances.append(
            {
                "substance_id": substance_id,
                "canonical_name": name,
                "canonical_cas": "",
                "parent_substance_id": "",
                "chemical_form": "regulatory_group",
                "source": "local regulatory lists",
            }
        )
        for alias in _local_aliases(name):
            _add_alias(
                aliases,
                alias_seen,
                substance_id=substance_id,
                canonical_cas="",
                alias=alias,
                language="es",
                alias_type="regulatory_group",
                source="Rainforest Alliance local list",
                confidence="high",
                enabled="true",
            )

    return substances, aliases, failures


def _write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    substances, aliases, failures = build_registry()
    _write_csv(
        SUBSTANCES_PATH,
        substances,
        [
            "substance_id",
            "canonical_name",
            "canonical_cas",
            "parent_substance_id",
            "chemical_form",
            "source",
        ],
    )
    _write_csv(
        ALIASES_PATH,
        aliases,
        [
            "substance_id",
            "canonical_cas",
            "alias",
            "language",
            "alias_type",
            "source",
            "confidence",
            "enabled",
        ],
    )
    print(
        json.dumps(
            {
                "substances": len(substances),
                "aliases": len(aliases),
                "enabled_aliases": sum(row["enabled"] == "true" for row in aliases),
                "pubchem_failures": failures,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if failures and len(failures) > 20:
        raise SystemExit("Too many PubChem lookup failures; registry not considered reproducible.")


if __name__ == "__main__":
    main()
