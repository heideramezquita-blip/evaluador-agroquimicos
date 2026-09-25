import unittest

from src.text_utils import active_name_local_to_cas, names_equivalent


class NameMatchingTests(unittest.TestCase):
    def test_word_order_and_punctuation(self):
        self.assertTrue(names_equivalent("Cihalotrina, lambda", "Lambda-cihalotrina"))

    def test_accents(self):
        self.assertTrue(names_equivalent("Deltametrina", "DELTAMETRINA"))

    def test_no_fuzzy_spelling(self):
        self.assertFalse(names_equivalent("Malatión", "Malathion"))
        self.assertFalse(names_equivalent("Zeta-cipermetrina", "Cipermetrina"))

    def test_semicolon_variants(self):
        self.assertTrue(names_equivalent("Endosulfán; alfa-endosulfán; beta endosulfán*", "alfa-endosulfán"))

    def test_local_active_name_rejects_neighboring_other_cas(self):
        context = (
            "Tiametoxam | 153719-23-4 | 15% | Hydrocarbon | "
            "64742-94-5 | 10%"
        )
        self.assertFalse(active_name_local_to_cas("Tiametoxam", "64742-94-5", context))
        self.assertTrue(active_name_local_to_cas("Tiametoxam", "153719-23-4", context))


if __name__ == "__main__":
    unittest.main()
