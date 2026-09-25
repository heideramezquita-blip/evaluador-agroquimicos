from __future__ import annotations

import csv
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.cas_extractor import extract_document_cas, merge_cas_records
from src.master_database import MasterDatabase
from src.name_fallback import extract_explicit_active_names
from src.pdf_reader import read_pdf
from src.rules import apply_rules


def _pdfs(corpus: Path) -> list[Path]:
    return sorted(p for p in corpus.rglob("*") if p.is_file() and p.suffix.lower() == ".pdf")


def _document_analysis(path: Path, corpus: Path, master: MasterDatabase) -> tuple[dict, object, list, list, list]:
    doc = read_pdf(path.read_bytes(), path.name)
    records, invalid = extract_document_cas(doc)
    active_names = extract_explicit_active_names([doc])
    matches = []
    for rec in records:
        matches.extend(
            master.match_cas(
                rec.cas,
                active_confirmed=rec.active_confirmed,
                active_names=active_names,
                occurrence_contexts=[
                    {
                        "source_file": occurrence.source_file,
                        "page": occurrence.page,
                        "context": occurrence.context,
                    }
                    for occurrence in rec.occurrences
                ],
            )
        )
    evaluation = apply_rules(records, matches, doc.warnings)
    row = {
        "file": str(path.relative_to(corpus)),
        "processable": doc.processable,
        "characters": doc.character_count,
        "valid_cas_count": len(records),
        "valid_cas": ";".join(r.cas for r in records),
        "invalid_candidate_count": len(invalid),
        "explicit_active_names": ";".join(item["name"] for item in active_names),
        "matches": ";".join(f"{m.cas}:{m.source_list}:{m.applied_action}" for m in evaluation.matches),
        "status": evaluation.status,
    }
    return row, doc, records, invalid, active_names


def _product_id(name: str) -> str | None:
    match = re.match(r"^(\d+(?:\.\d+)?)(?:\.|\s)", name)
    return match.group(1) if match else None


def _paired_cases(corpus: Path) -> list[tuple[str, str, Path, Path]]:
    pairs: list[tuple[str, str, Path, Path]] = []
    for ft_dir, hs_dir, suite in (("FT", "HS", "principal"), ("SFT", "SHS", "suplementario")):
        ft = {
            _product_id(p.name): p
            for p in (corpus / ft_dir).iterdir()
            if p.is_file() and p.suffix.lower() == ".pdf" and _product_id(p.name)
        }
        hs = {
            _product_id(p.name): p
            for p in (corpus / hs_dir).iterdir()
            if p.is_file() and p.suffix.lower() == ".pdf" and _product_id(p.name)
        }
        common = sorted(
            set(ft) & set(hs),
            key=lambda value: tuple(int(x) for x in value.split(".")),
        )
        for product_id in common:
            pairs.append((suite, product_id, ft[product_id], hs[product_id]))
    return pairs


def main() -> int:
    if len(sys.argv) != 2:
        print("Uso: python scripts/audit_corpus.py /ruta/al/corpus")
        return 2

    corpus = Path(sys.argv[1])
    master = MasterDatabase(ROOT / "data" / "master_restrictions.csv")
    rows = []
    statuses = Counter()
    cache: dict[Path, tuple] = {}

    for path in _pdfs(corpus):
        analyzed = _document_analysis(path, corpus, master)
        cache[path] = analyzed
        row = analyzed[0]
        rows.append(row)
        statuses[row["status"]] += 1

    document_output = ROOT / "corpus_audit_documents.csv"
    with document_output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    pair_rows = []
    pair_statuses = Counter()
    for suite, product_id, ft_path, hs_path in _paired_cases(corpus):
        analyses = [cache[ft_path], cache[hs_path]]
        docs = [a[1] for a in analyses]
        records = merge_cas_records([a[2] for a in analyses])
        active_names = extract_explicit_active_names(docs)
        matches = []
        for rec in records:
            matches.extend(
                master.match_cas(
                    rec.cas,
                    active_confirmed=rec.active_confirmed,
                    active_names=active_names,
                    occurrence_contexts=[
                        {
                            "source_file": occurrence.source_file,
                            "page": occurrence.page,
                            "context": occurrence.context,
                        }
                        for occurrence in rec.occurrences
                    ],
                )
            )
        warnings = [w for doc in docs for w in doc.warnings]
        evaluation = apply_rules(records, matches, warnings)
        pair_statuses[evaluation.status] += 1
        pair_rows.append({
            "suite": suite,
            "product_id": product_id,
            "ft_file": ft_path.name,
            "hs_file": hs_path.name,
            "both_processable": all(doc.processable for doc in docs),
            "valid_cas_count": len(records),
            "valid_cas": ";".join(r.cas for r in records),
            "explicit_active_names": ";".join(item["name"] for item in active_names),
            "matches": ";".join(f"{m.cas}:{m.source_list}:{m.applied_action}" for m in evaluation.matches),
            "status": evaluation.status,
        })

    pair_output = ROOT / "corpus_audit_pairs.csv"
    with pair_output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=pair_rows[0].keys())
        writer.writeheader()
        writer.writerows(pair_rows)

    print(f"Documentos: {len(rows)}")
    print(f"Procesables: {sum(str(r['processable']).lower() == 'true' for r in rows)}")
    print(f"Con >=1 CAS válido: {sum(int(r['valid_cas_count']) > 0 for r in rows)}")
    print("Estados por documento:")
    for status, count in statuses.items():
        print(f"  {status}: {count}")
    print(f"Pares FT/HS: {len(pair_rows)}")
    print(f"Pares con >=1 CAS válido: {sum(int(r['valid_cas_count']) > 0 for r in pair_rows)}")
    print("Estados por par:")
    for status, count in pair_statuses.items():
        print(f"  {status}: {count}")
    print(f"Informe documentos: {document_output}")
    print(f"Informe pares: {pair_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
