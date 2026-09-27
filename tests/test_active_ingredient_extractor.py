import unittest

from src.active_ingredient_extractor import extract_active_ingredients
from src.models import PdfDocument, PdfPage, PdfTextBlock


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

    def test_two_column_kadabra_layout_uses_aligned_identity_blocks_only(self):
        page = PdfPage(
            page=1,
            text=(
                "Modo de Acción:                         Ingrediente activo:\n"
                "Bifentrina: Insecticida...             Bifentrina (360 g/L) +\n"
                "Fipronil: Insecticida...               Fipronil (120 g/L)\n"
                "Generalidades: KADABRA es un insecticida a base de los "
                "ingredientes activos Bifentrina y Fipronil."
            ),
            blocks=[
                PdfTextBlock(452, 428, 555, 442, "Ingrediente activo:\n"),
                PdfTextBlock(67, 449, 158, 463, "Modo de Acción:\n"),
                PdfTextBlock(
                    452,
                    445,
                    538,
                    467,
                    "Bifentrina (360 g/L) +\nFipronil (120 g/L)\n",
                ),
                PdfTextBlock(
                    67,
                    465,
                    428,
                    521,
                    "Bifentrina: Insecticida de contacto con acción estomacal.\n"
                    "Fipronil: Insecticida que actúa por contacto e ingestión.\n",
                ),
                PdfTextBlock(
                    452,
                    482,
                    529,
                    531,
                    "Categoría toxicológica:\nII – Moderadamente Peligroso.\n",
                ),
                PdfTextBlock(
                    67,
                    626,
                    429,
                    717,
                    "Generalidades:\nKADABRA 480 SC es un insecticida a base de los "
                    "ingredientes activos Bifentrina y Fipronil.\n"
                    "Bifentrina es un piretroide de cuarta generación.\n",
                ),
            ],
        )
        doc = PdfDocument(
            file_name="FT Kadabra.pdf",
            pages=[page],
            page_count=1,
            character_count=len(page.text),
            pages_with_text=1,
            processable=True,
            warnings=[],
        )

        items = extract_active_ingredients(doc)

        self.assertEqual(
            [(item.name, item.concentration) for item in items],
            [("Bifentrina", "360 g/L"), ("Fipronil", "120 g/L")],
        )

    def test_narrative_mention_of_ingredients_activos_does_not_open_identity_block(self):
        text = (
            "Generalidades:\n"
            "KADABRA es un insecticida a base de los ingredientes activos "
            "Bifentrina y Fipronil.\n"
            "Bifentrina es un piretroide de cuarta generación.\n"
        )
        self.assertEqual(extract_active_ingredients(document(text)), [])

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
