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
    def to_dict(self)->dict[str,Any]:
        return {"cas":self.cas,"active_confirmed":self.active_confirmed,"occurrences":[asdict(o) for o in self.occurrences]}

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

@dataclass
class Evaluation:
    status: str
    message: str
    hits: list[EvidenceHit] = field(default_factory=list)
    cas_records: list[CasRecord] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    def to_dict(self):
        return {"status":self.status,"message":self.message,"hits":[asdict(h) for h in self.hits],"cas_records":[r.to_dict() for r in self.cas_records],"warnings":list(self.warnings)}
