from __future__ import annotations

import fitz

from .models import PdfDocument, PdfPage, PdfTextBlock
from .text_utils import normalize_text


MIN_EXTRACTABLE_CHARS = 50


def _repeated_text_shell(pages: list[PdfPage]) -> bool:
    """Detect multi-page files where extraction only returns the same shell."""
    if len(pages) < 2 or any(not page.text for page in pages):
        return False

    signatures = [normalize_text(page.text) for page in pages]
    return bool(signatures[0]) and len(set(signatures)) == 1


def read_pdf(pdf_bytes: bytes, file_name: str) -> PdfDocument:
    document = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages: list[PdfPage] = []
    total_chars = 0
    pages_with_text = 0

    try:
        for page_number, page in enumerate(document, start=1):
            text = page.get_text("text", sort=True) or ""
            if not text.strip():
                text = page.get_text("text") or ""
            text = text.strip()

            blocks = []
            for block in page.get_text("blocks", sort=True) or []:
                x0, y0, x1, y1, block_text = block[:5]
                block_text = (block_text or "").strip()
                if not block_text:
                    continue
                blocks.append(
                    PdfTextBlock(
                        float(x0),
                        float(y0),
                        float(x1),
                        float(y1),
                        block_text,
                    )
                )

            total_chars += len(text)
            if text:
                pages_with_text += 1
            pages.append(PdfPage(page=page_number, text=text, blocks=blocks))
    finally:
        document.close()

    repeated_shell = _repeated_text_shell(pages)
    processable = total_chars >= MIN_EXTRACTABLE_CHARS and not repeated_shell
    warnings: list[str] = []

    if repeated_shell:
        warnings.append(
            "Solo se extrajo texto repetido de encabezado o pie de página; "
            "el contenido principal parece no ser extraíble. Use otro PDF, "
            "CAS manual o revisión humana."
        )
    elif not processable:
        warnings.append(
            "No se encontró texto extraíble suficiente. El documento puede "
            "estar escaneado; use CAS manual o revisión humana."
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
