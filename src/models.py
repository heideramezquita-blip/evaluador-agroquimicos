from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class PdfPage:
    page: int
    text: str


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
        return any(o.role == "active_explicit" for o in self.occurrences)

    @property
    def sources(self) -> list[str]:
        return sorted({o.source for o in self.occurrences})

    def to_dict(self) -> dict[str, Any]:
        return {
            "cas": self.cas,
            "active_confirmed": self.active_confirmed,
            "sources": self.sources,
            "occurrences": [asdict(o) for o in self.occurrences],
        }


@dataclass
class RestrictionMatch:
    cas: str
    source_list: str
    action: str
    scope: str
    ingredient: str
    usage: str
    criteria: str
    source_code: str
    source_version: str
    source_date: str
    active_confirmed: bool = False
    active_evidence: str = ""
    applied_action: str = ""
    rationale: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Evaluation:
    status: str
    message: str
    cas_records: list[CasRecord]
    matches: list[RestrictionMatch] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "message": self.message,
            "cas_records": [r.to_dict() for r in self.cas_records],
            "matches": [m.to_dict() for m in self.matches],
            "warnings": list(self.warnings),
        }
