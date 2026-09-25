import unittest

import fitz

from src.pdf_reader import read_pdf


class PdfReaderTests(unittest.TestCase):
    def test_blank_pdf_is_not_processable(self):
        doc = fitz.open()
        doc.new_page()
        payload = doc.tobytes()
        doc.close()

        result = read_pdf(payload, "scan_like.pdf")
        self.assertFalse(result.processable)
        self.assertEqual(result.character_count, 0)
        self.assertTrue(result.warnings)


if __name__ == "__main__":
    unittest.main()
