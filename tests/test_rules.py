import unittest
from pathlib import Path

from src.master_database import MasterDatabase
from src.models import CasOccurrence, CasRecord
from src.rules import (
    STATUS_MITIGATION,
    STATUS_NO_USE,
    STATUS_REVIEW,
    apply_rules,
)


MASTER = Path(__file__).resolve().parents[1] / "data" / "master_restrictions.csv"


def record(cas: str, active: bool) -> CasRecord:
    return CasRecord(
        cas=cas,
        occurrences=[
            CasOccurrence(
                cas=cas,
                source_file="test.pdf",
                page=1,
                source="document",
                role="active_explicit" if active else "component",
            )
        ],
    )


class RuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = MasterDatabase(MASTER)

    def evaluate(self, rec: CasRecord):
        matches = self.db.match_cas(rec.cas, active_confirmed=rec.active_confirmed)
        return apply_rules([rec], matches)

    def test_prohibited_active_is_no_use(self):
        result = self.evaluate(record("153719-23-4", True))
        self.assertEqual(result.status, STATUS_NO_USE)

    def test_prohibited_unconfirmed_role_is_review(self):
        result = self.evaluate(record("153719-23-4", False))
        self.assertEqual(result.status, STATUS_REVIEW)

    def test_mitigation_active(self):
        result = self.evaluate(record("52918-63-5", True))
        self.assertEqual(result.status, STATUS_MITIGATION)

    def test_obsolete_is_review(self):
        result = self.evaluate(record("309-00-2", True))
        self.assertEqual(result.status, STATUS_REVIEW)

    def test_prohibited_can_be_confirmed_by_explicit_active_name(self):
        rec = record("153719-23-4", False)
        matches = self.db.match_cas(
            rec.cas,
            active_confirmed=False,
            active_names=[{
                "name": "Tiametoxam",
                "source_file": "FT.pdf",
                "page": 1,
            }],
        )
        result = apply_rules([rec], matches)
        self.assertEqual(result.status, STATUS_NO_USE)
        self.assertTrue(matches[0].active_confirmed)

    def test_lambda_name_order_is_confirmed_conservatively(self):
        rec = record("91465-08-6", False)
        matches = self.db.match_cas(
            rec.cas,
            active_confirmed=False,
            active_names=[{
                "name": "Lambda-cihalotrina",
                "source_file": "FT.pdf",
                "page": 1,
            }],
        )
        result = apply_rules([rec], matches)
        self.assertEqual(result.status, STATUS_MITIGATION)
        self.assertTrue(matches[0].active_confirmed)


class ContextRoleConfirmationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = MasterDatabase(MASTER)

    def test_role_can_be_confirmed_from_local_cas_context(self):
        rec = record("121-75-5", False)
        matches = self.db.match_cas(
            rec.cas,
            active_confirmed=False,
            active_names=[{"name": "Malathion", "source_file": "FT.pdf", "page": 1}],
            occurrence_contexts=[{
                "source_file": "HS.pdf",
                "page": 1,
                "context": "CAS 121-75-5 ... Malathion ... 604 gr/L",
            }],
        )
        result = apply_rules([rec], matches)
        self.assertEqual(result.status, STATUS_MITIGATION)
        self.assertTrue(matches[0].active_confirmed)

    def test_context_confirmation_does_not_use_substring_fuzzy_match(self):
        rec = record("52315-07-8", False)
        matches = self.db.match_cas(
            rec.cas,
            active_confirmed=False,
            active_names=[{"name": "Cipermetrina", "source_file": "FT.pdf", "page": 1}],
            occurrence_contexts=[{
                "source_file": "HS.pdf",
                "page": 2,
                "context": "CAS 52315-07-8 zeta-cipermetrina",
            }],
        )
        result = apply_rules([rec], matches)
        self.assertEqual(result.status, STATUS_REVIEW)
        self.assertFalse(matches[0].active_confirmed)


if __name__ == "__main__":
    unittest.main()
