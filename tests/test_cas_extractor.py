import unittest

from src.cas_extractor import merge_cas_records
from src.models import CasOccurrence, CasRecord


class CasExtractorTests(unittest.TestCase):
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
