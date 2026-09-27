import unittest

from src.active_ingredient_extractor import extract_active_ingredients
from src.composition_extractor import extract_composition_components
from src.models import PdfDocument, PdfPage, PdfTextBlock


class CompositionExtractorTests(unittest.TestCase):
    def _mayoral_document(self):
        page = PdfPage(
            page=2,
            text=(
                "SECCIÓN 3: Composición/información sobre los componentes\n"
                "Sustancia\nNo es aplicable\nMezcla\n"
                "Nombre químico Nº CAS % en peso Nº CE INTERNATIONAL GHS CLASSIFICATION Factor M\n"
                "Imazapic 104098-48- 21-27 Eye Irrit. 2 (H319)\n"
                "8 Aquatic Acute 1 (H400)\n"
                "Isopropylamine 75-31-0 6-10 200-860-9 Flam. Liq. 1 (H224)\n"
                "Imazapyr 81334-34-1 6-10 Eye Irrit. 2 (H319)\n"
                "SECCIÓN 4: Primeros auxilios\n"
            ),
            blocks=[
                PdfTextBlock(
                    96.7, 327.0, 495.1, 337.0,
                    "Nombre químico\nNº CAS\n% en peso\nNº CE\nINTERNATIONAL GHS\n",
                ),
                PdfTextBlock(530.5, 327.0, 570.4, 337.0, "Factor M\n"),
                PdfTextBlock(407.2, 337.3, 485.1, 347.4, "CLASSIFICATION\n"),
                PdfTextBlock(114.2, 348.2, 259.4, 358.2, "Imazapic\n104098-48-\n"),
                PdfTextBlock(233.9, 358.5, 241.4, 368.6, "8\n"),
                PdfTextBlock(
                    277.0, 348.2, 494.2, 368.6,
                    "21-27\nEye Irrit. 2 (H319)\nAquatic Acute 1 (H400)\n",
                ),
                PdfTextBlock(
                    101.7, 380.0, 487.6, 421.1,
                    "Isopropylamine\n75-31-0\n6-10\n200-860-9\n"
                    "Flam. Liq. 1 (H224)\nAcute Tox. 3 (H301)\n",
                ),
                PdfTextBlock(
                    113.7, 463.5, 497.9, 483.9,
                    "Imazapyr\n81334-34-1\n6-10\nEye Irrit. 2 (H319)\n",
                ),
                PdfTextBlock(54.7, 496.2, 229.8, 509.6, "SECCIÓN 4: Primeros auxilios\n"),
            ],
        )
        return PdfDocument(
            file_name="HS Mayoral.PDF",
            pages=[page],
            page_count=1,
            character_count=len(page.text),
            pages_with_text=1,
            processable=True,
            warnings=[],
        )

    def test_mayoral_composition_rows_are_exposed_with_identity(self):
        items = extract_composition_components(self._mayoral_document())

        self.assertEqual(
            [(item.name, item.cas, item.concentration) for item in items],
            [
                ("Imazapic", "104098-48-8", "21-27"),
                ("Isopropylamine", "75-31-0", "6-10"),
                ("Imazapyr", "81334-34-1", "6-10"),
            ],
        )

    def test_mayoral_sds_components_are_not_promoted_to_active_ingredients(self):
        self.assertEqual(extract_active_ingredients(self._mayoral_document()), [])


if __name__ == "__main__":
    unittest.main()
