import unittest
from collections import Counter
from pathlib import Path

from src.master_database import MasterDatabase
from src.cas_utils import is_valid_cas


MASTER = Path(__file__).resolve().parents[1] / "data" / "master_restrictions.csv"


class MasterDatabaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = MasterDatabase(MASTER)

    def test_normalized_master_row_counts(self):
        counts = Counter(row["source_list"] for row in self.db.rows)
        self.assertEqual(counts["PROHIBITED"], 165)
        self.assertEqual(counts["MITIGATE_RISK"], 168)
        self.assertEqual(counts["OBSOLETE"], 24)
        self.assertEqual(counts["CARBAMATE"], 12)
        self.assertEqual(counts["ORGANOPHOSPHATE"], 46)

    def test_all_nonblank_master_cas_are_valid(self):
        invalid = [row["cas"] for row in self.db.rows if row["cas"] and not is_valid_cas(row["cas"])]
        self.assertEqual(invalid, [])

    def test_known_prohibited_entry(self):
        matches = self.db.match_cas(
            "153719-23-4",
            active_confirmed=True,
        )
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].ingredient, "Tiametoxam")
        self.assertEqual(matches[0].action, "NO_UTILIZAR")

    def test_mitigation_scope_is_conservative(self):
        matches = self.db.match_cas(
            "91465-08-6",
            active_confirmed=False,
        )
        self.assertEqual(matches[0].scope, "ROLE_CONFIRMATION_REQUIRED")
        self.assertFalse(matches[0].active_confirmed)


if __name__ == "__main__":
    unittest.main()
