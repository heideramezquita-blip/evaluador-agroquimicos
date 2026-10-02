from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class PdfTextBlock:
    x0: float
    y0: float
    x1: float
    y1: float
    text: str


@dataclass
class PdfPage:
    page: int
    text: str
    blocks: list[PdfTextBlock] = field(default_factory=list)


@dataclass
class PdfDocument:
    file_name: str
    pages: list[PdfPage]
    page_count: int
    character_count: int
    pages_with_text: int
    processable: bool
    warnings: list[str] = field(default_factory=list)


@dataclass
class ActiveIngredientEvidence:
    name: str
    source_file: str
    page: int
    concentration: str = ""
    cas: str = ""
    context: str = ""


@dataclass
class CompositionComponentEvidence:
    name: str
    source_file: str
    page: int
    concentration: str = ""
    cas: str = ""
    context: str = ""


@dataclass
class CasOccurrence:
    cas: str
    source_file: str
    page: int | None
    source: str
    role: str = "unknown"
    context: str = ""
    note: str = ""


@dataclass
class CasRecord:
    cas: str
    occurrences: list[CasOccurrence] = field(default_factory=list)

    @property
    def active_confirmed(self) -> bool:
        return any(
            occurrence.role == "active_explicit"
            for occurrence in self.occurrences
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "cas": self.cas,
            "active_confirmed": self.active_confirmed,
            "occurrences": [
                asdict(occurrence)
                for occurrence in self.occurrences
            ],
        }


@dataclass(frozen=True)
class ProhibitedEntry:
    ingredient: str
    cas: str
    usage: str
    criteria: str
    source_code: str
    source_version: str
    source_date: str
    is_group: bool = False
    source_list: str = "PROHIBITED"
    action: str = "NO_UTILIZAR"


@dataclass
class EvidenceHit:
    entry: ProhibitedEntry
    channel: str
    matched_value: str
    source_file: str
    page: int | None
    context: str
    context_class: str
    strength: str
    rationale: str
    substance_id: str = ""
    canonical_name: str = ""
    alias_language: str = ""
    alias_type: str = ""
    alias_source: str = ""


@dataclass
class Evaluation:
    status: str
    message: str
    hits: list[EvidenceHit] = field(default_factory=list)
    cas_records: list[CasRecord] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "message": self.message,
            "hits": [asdict(hit) for hit in self.hits],
            "cas_records": [
                record.to_dict()
                for record in self.cas_records
            ],
            "warnings": list(self.warnings),
        }
