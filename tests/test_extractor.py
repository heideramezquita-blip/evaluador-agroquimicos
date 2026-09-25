import unittest

from src.cas_extractor import extract_document_cas
from src.models import PdfDocument, PdfPage


class ExtractorTests(unittest.TestCase):
    def test_active_context(self):
        doc = PdfDocument(
            file_name="x.pdf",
            pages=[PdfPage(1, "Ingrediente activo\nNo CAS Ingrediente Activo\n153719-23-4\nConcentración")],
            page_count=1,
            character_count=80,
            pages_with_text=1,
            processable=True,
        )
        records, invalid = extract_document_cas(doc)
        self.assertEqual(records[0].cas, "153719-23-4")
        self.assertTrue(records[0].active_confirmed)
        self.assertEqual(invalid, [])

    def test_invalid_candidate_is_discarded(self):
        doc = PdfDocument(
            file_name="x.pdf",
            pages=[PdfPage(1, "Componente 167-00-5")],
            page_count=1,
            character_count=80,
            pages_with_text=1,
            processable=True,
        )
        records, invalid = extract_document_cas(doc)
        self.assertEqual(records, [])
        self.assertEqual(invalid[0]["candidate"], "167-00-5")


if __name__ == "__main__":
    unittest.main()
