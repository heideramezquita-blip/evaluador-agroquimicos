import unittest

from src.cas_utils import (
    extract_valid_cas,
    is_valid_cas,
    parse_manual_cas,
    reconstruct_split_cas,
)


class CasTests(unittest.TestCase):
    def test_checksum(self):
        self.assertTrue(is_valid_cas("153719-23-4"))
        self.assertFalse(is_valid_cas("167-00-5"))

    def test_variants(self):
        for value in (
            "153719-23-4",
            "153719 - 23 - 4",
            "153719-\n23-4",
            "153719–23–4",
            "153719\u00ad23\u00ad4",
        ):
            with self.subTest(value=value):
                self.assertEqual(extract_valid_cas(value), ["153719-23-4"])

    def test_eu_index_number_is_not_parsed_as_cas(self):
        self.assertEqual(extract_valid_cas("613-167-00-5"), [])
        self.assertEqual(
            extract_valid_cas("55965-84-9 613-167-00-5"),
            ["55965-84-9"],
        )

    def test_manual_digits(self):
        self.assertIn("153719-23-4", parse_manual_cas("153719234")[0])

    def test_reconstruct_split_cas_validates_checksum(self):
        self.assertEqual(
            reconstruct_split_cas("104098-48-", "8"),
            "104098-48-8",
        )
        self.assertIsNone(reconstruct_split_cas("104098-48-", "7"))


if __name__ == "__main__":
    unittest.main()
