from __future__ import annotations

import csv
import os
import re
import sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.engine import analyze  # noqa: E402


MASTER = ROOT / "data" / "master_restrictions.csv"
MAX_WORKERS = min(12, os.cpu_count() or 1)

DOCUMENT_FIELDS = ("file", "status", "processable", "valid_cas", "hits")
PAIR_FIELDS = (
    "suite",
    "product_id",
    "ft",
    "hs",
    "status",
    "unprocessables",
    "hits",
    "decision_hits",
)


def product_id(name: str) -> str | None:
    match = re.match(r"^(\d+(?:\.\d+)?)(?:\.|\s)", name)
    return match.group(1) if match else None


def evaluate_files(items):
    result = analyze(
        [(path.name, path.read_bytes()) for path in items],
        master_path=MASTER,
    )
    return result, result["evaluation"]


def audit_document(path: Path) -> dict:
    result, evaluation = evaluate_files([path])
    return {
        "file": str(path),
        "status": evaluation.status,
        "processable": bool(result["documents"])
        and all(document.processable for document in result["documents"]),
        "valid_cas": ";".join(record.cas for record in evaluation.cas_records),
        "hits": " || ".join(
            f"{hit.entry.ingredient}|{hit.channel}|{hit.context_class}|p{hit.page}"
            for hit in result["all_hits"]
        ),
    }


def _pdf_map(directory: Path) -> dict[str, Path]:
    if not directory.exists():
        return {}
    return {
        product_id(path.name): path
        for path in directory.iterdir()
        if path.is_file()
        and path.suffix.lower() == ".pdf"
        and product_id(path.name)
    }


def pair_specs(corpus: Path):
    specs = []
    for ft_dir, hs_dir, suite in (
        ("FT", "HS", "principal"),
        ("SFT", "SHS", "suplementario"),
    ):
        ft_files = _pdf_map(corpus / ft_dir)
        hs_files = _pdf_map(corpus / hs_dir)
        shared_ids = sorted(
            set(ft_files) & set(hs_files),
            key=lambda value: tuple(map(int, value.split("."))),
        )
        specs.extend(
            (suite, item_id, ft_files[item_id], hs_files[item_id])
            for item_id in shared_ids
        )
    return specs


def audit_pair(spec) -> dict:
    suite, item_id, ft, hs = spec
    result, evaluation = evaluate_files([ft, hs])
    return {
        "suite": suite,
        "product_id": item_id,
        "ft": ft.name,
        "hs": hs.name,
        "status": evaluation.status,
        "unprocessables": sum(
            not document.processable for document in result["documents"]
        ),
        "hits": " || ".join(
            f"{hit.entry.ingredient}|{hit.channel}|{hit.context_class}|{hit.source_file}|p{hit.page}"
            for hit in result["all_hits"]
        ),
        "decision_hits": " || ".join(
            f"{hit.entry.ingredient}|{hit.channel}|{hit.context_class}|{hit.source_file}|p{hit.page}"
            for hit in evaluation.hits
        ),
    }


def write_csv(path: Path, fieldnames, rows) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def parallel_map(function, items):
    if not items:
        return []
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        return list(executor.map(function, items))


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("Uso: python scripts/audit_corpus.py <corpus> [all|docs|pairs]")

    corpus = Path(sys.argv[1])
    mode = sys.argv[2] if len(sys.argv) > 2 else "all"
    if mode not in {"all", "docs", "pairs"}:
        raise SystemExit("Modo inválido. Use: all, docs o pairs.")

    pdfs = sorted(
        path
        for path in corpus.rglob("*")
        if path.is_file() and path.suffix.lower() == ".pdf"
    )
    pairs = pair_specs(corpus)

    if mode in {"docs", "all"}:
        documents = parallel_map(audit_document, pdfs)
        write_csv(
            ROOT / "validation_corpus_documents.csv",
            DOCUMENT_FIELDS,
            documents,
        )
        print("PDF", len(documents), Counter(row["status"] for row in documents))

    if mode in {"pairs", "all"}:
        pair_rows = parallel_map(audit_pair, pairs)
        write_csv(
            ROOT / "validation_corpus_pairs.csv",
            PAIR_FIELDS,
            pair_rows,
        )
        print("PARES", len(pair_rows), Counter(row["status"] for row in pair_rows))


if __name__ == "__main__":
    main()
