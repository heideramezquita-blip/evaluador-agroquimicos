from __future__ import annotations

import fitz

from .models import PdfDocument, PdfPage


MIN_EXTRACTABLE_CHARS = 50


def read_pdf(pdf_bytes: bytes, file_name: str) -> PdfDocument:
    document = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages: list[PdfPage] = []
    total_chars = 0
    pages_with_text = 0

    try:
        for page_number, page in enumerate(document, start=1):
            text = page.get_text("text") or ""
            text = text.strip()
            total_chars += len(text)
            if text:
                pages_with_text += 1
            pages.append(PdfPage(page=page_number, text=text))
    finally:
        document.close()

    processable = total_chars >= MIN_EXTRACTABLE_CHARS
    warnings: list[str] = []
    if not processable:
        warnings.append(
            "No se encontró texto extraíble suficiente. El documento puede estar escaneado; use CAS manual o revisión humana."
        )

    return PdfDocument(
        file_name=file_name,
        pages=pages,
        page_count=len(pages),
        character_count=total_chars,
        pages_with_text=pages_with_text,
        processable=processable,
        warnings=warnings,
    )
