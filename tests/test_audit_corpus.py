import tempfile
import unittest
from pathlib import Path

from scripts.audit_corpus import pair_specs, product_id


class AuditCorpusTests(unittest.TestCase):
    def test_product_id_parses_primary_and_decimal_prefixes(self):
        self.assertEqual(product_id("14. FT Producto.pdf"), "14")
        self.assertEqual(product_id("14.1 HS Producto.pdf"), "14.1")
        self.assertIsNone(product_id("sin-prefijo.pdf"))

    def test_pair_specs_tolerates_missing_optional_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            corpus = Path(tmp)
            (corpus / "FT").mkdir()
            (corpus / "HS").mkdir()
            self.assertEqual(pair_specs(corpus), [])


if __name__ == "__main__":
    unittest.main()
