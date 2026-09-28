import unittest

from src.cas_extractor import extract_document_cas, merge_cas_records
from src.models import CasOccurrence, CasRecord, PdfDocument, PdfPage, PdfTextBlock


class CasExtractorTests(unittest.TestCase):
    def test_recovers_checksum_digit_split_into_neighbouring_pdf_block(self):
        page = PdfPage(
            page=2,
            text=(
                "SECCIÓN 3: Composición/información sobre los componentes\n"
                "Imazapic 104098-48- 21-27\n"
                "8 Aquatic Acute 1 (H400)\n"
            ),
            blocks=[
                PdfTextBlock(114.2, 348.2, 259.4, 358.2, "Imazapic\n104098-48-\n"),
                PdfTextBlock(233.9, 358.5, 241.4, 368.6, "8\n"),
                PdfTextBlock(277.0, 348.2, 494.2, 368.6, "21-27\nAquatic Acute 1 (H400)\n"),
            ],
        )
        doc = PdfDocument(
            file_name="HS Mayoral.PDF",
            pages=[page],
            page_count=1,
            character_count=len(page.text),
            pages_with_text=1,
            processable=True,
            warnings=[],
        )

        records, invalid = extract_document_cas(doc)

        self.assertEqual(invalid, [])
        self.assertEqual([record.cas for record in records], ["104098-48-8"])
        self.assertIn("bloques contiguos", records[0].occurrences[0].note)

    def test_merge_preserves_order_and_deduplicates_occurrences(self):
        first = CasOccurrence(
            "153719-23-4",
            "FT.pdf",
            1,
            "document",
            "active_explicit",
            "Ingrediente activo",
        )
        duplicate = CasOccurrence(
            "153719-23-4",
            "FT.pdf",
            1,
            "document",
            "unknown",
            "Ingrediente activo",
        )
        second = CasOccurrence(
            "153719-23-4",
            "HS.pdf",
            3,
            "document",
            "unknown",
            "Composición",
        )

        merged = merge_cas_records(
            [
                [CasRecord("153719-23-4", [first])],
                [CasRecord("153719-23-4", [duplicate, second])],
            ]
        )

        self.assertEqual([record.cas for record in merged], ["153719-23-4"])
        self.assertEqual(merged[0].occurrences, [first, second])


if __name__ == "__main__":
    unittest.main()
