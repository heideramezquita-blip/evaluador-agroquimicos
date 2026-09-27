import unittest

from src.active_ingredient_extractor import extract_active_ingredients
from src.models import PdfDocument, PdfPage


def document(text, name="test.pdf"):
    return PdfDocument(
        file_name=name,
        pages=[PdfPage(page=1, text=text)],
        page_count=1,
        character_count=len(text),
        pages_with_text=1,
        processable=True,
        warnings=[],
    )


class ActiveIngredientExtractorTests(unittest.TestCase):
    def test_becano_style_label_extracts_name_without_cas(self):
        text = (
            "FICHA TÉCNICA\n"
            "COMPOSICIÓN GARANTIZADA:\n"
            "Ingredientes activos:\n"
            "Indaziﬂam (formulación a 20ºC) / 500g/litro\n"
            "Ingredientes aditivos:\n"
            "c.s.p. 1 litro"
        )
        items = extract_active_ingredients(document(text, "FT Becano.pdf"))

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].name, "Indaziflam")
        self.assertEqual(items[0].concentration, "500g/litro")
        self.assertEqual(items[0].cas, "")
        self.assertEqual(items[0].source_file, "FT Becano.pdf")
        self.assertEqual(items[0].page, 1)

    def test_inline_active_ingredient_can_keep_concentration_and_cas(self):
        text = (
            "Ingrediente activo: Deltametrina 2.5% CAS 52918-63-5\n"
            "Uso agrícola"
        )
        items = extract_active_ingredients(document(text))

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].name, "Deltametrina")
        self.assertEqual(items[0].concentration, "2.5%")
        self.assertEqual(items[0].cas, "52918-63-5")

    def test_multiple_explicit_actives_are_reported_separately(self):
        text = (
            "COMPOSICIÓN GARANTIZADA\n"
            "Ingredientes Activos:\n"
            "Lambda-cihalotrina 106 g/L\n"
            "Tiametoxam 141 g/L\n"
            "Ingredientes aditivos:\n"
            "c.s.p. 1 L"
        )
        items = extract_active_ingredients(document(text))

        self.assertEqual(
            [(item.name, item.concentration) for item in items],
            [
                ("Lambda-cihalotrina", "106 g/L"),
                ("Tiametoxam", "141 g/L"),
            ],
        )

    def test_additives_are_not_promoted_to_active_ingredients(self):
        text = (
            "Ingredientes activos:\n"
            "Paraquat 200 g/L\n"
            "Ingredientes aditivos:\n"
            "Surfactante 20 g/L"
        )
        items = extract_active_ingredients(document(text))
        self.assertEqual([item.name for item in items], ["Paraquat"])

    def test_marker_without_ingredient_does_not_create_identity(self):
        text = (
            "Ingredientes activos:\n"
            "Ingredientes aditivos:\n"
            "c.s.p. 1 L"
        )
        self.assertEqual(extract_active_ingredients(document(text)), [])


if __name__ == "__main__":
    unittest.main()
