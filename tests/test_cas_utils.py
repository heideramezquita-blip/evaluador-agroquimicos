import unittest

from src.cas_utils import extract_valid_cas, is_valid_cas, parse_manual_cas


class CasUtilsTests(unittest.TestCase):
    def test_valid_control_digit(self):
        self.assertTrue(is_valid_cas("131860-33-8"))
        self.assertTrue(is_valid_cas("153719-23-4"))
        self.assertFalse(is_valid_cas("167-00-5"))

    def test_extract_and_dedupe_at_callsite(self):
        text = "CAS 153719-23-4 y 91465-08-6. Repite 153719-23-4."
        self.assertEqual(extract_valid_cas(text), ["153719-23-4", "91465-08-6"])

    def test_manual_accepts_digits_only(self):
        valid, invalid = parse_manual_cas("153719234; 91465-08-6; 167-00-5")
        self.assertIn("153719-23-4", valid)
        self.assertIn("91465-08-6", valid)
        self.assertIn("167-00-5", invalid)


if __name__ == "__main__":
    unittest.main()
