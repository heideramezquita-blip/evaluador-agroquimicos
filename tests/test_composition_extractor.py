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

    def test_coragen_split_header_and_identifier_column_are_parsed(self):
        page = PdfPage(
            page=3,
            text=(
                "SECCIÓN 3. Composición/información sobre los componentes\n"
                "3.2 Mezclas\n"
                "Componentes\nNombre químico\nNo. CAS\nNo. CE\nNo. Indice\n"
                "Número de registro\nClasificación\nConcentración (% w/w)\n"
                "Clorantraniliprol\n500008-45-7\n>= 10 - < 20\n"
                "Masa de reacción de 5-cloro-2-metil-2H-isotiazol-3-ona y "
                "2-metil-2H-isotiazol-3-ona (3:1)\n"
                "55965-84-9\n613-167-00-5\n>= 0,0002 - < 0,0015\n"
            ),
            blocks=[
                PdfTextBlock(
                    92.2, 372.4, 340.0, 430.4,
                    "Componentes\nNombre químico\nNo. CAS\nNo. CE\n"
                    "No. Indice\nNúmero de registro\n",
                ),
                PdfTextBlock(357.9, 384.8, 531.5, 395.9, "Clasificación\nConcentración\n"),
                PdfTextBlock(478.8, 396.3, 517.1, 407.4, "(% w/w)\n"),
                PdfTextBlock(92.2, 431.6, 311.2, 465.6, "Clorantraniliprol\n500008-45-7\n"),
                PdfTextBlock(357.9, 431.6, 453.0, 546.1, "Aquatic Acute 1;\nH400\nAquatic Chronic 1;\nH410\n"),
                PdfTextBlock(469.4, 431.6, 526.4, 442.7, ">= 10 - < 20\n"),
                PdfTextBlock(
                    92.2, 547.0, 241.6, 581.2,
                    "Masa de reacción de 5-cloro-2-\nmetil-2H-isotiazol-3-ona y "
                    "2-metil-\n2H-isotiazol-3-ona (3:1)\n",
                ),
                PdfTextBlock(251.7, 547.0, 314.5, 592.7, "55965-84-9\n\n613-167-00-5\n"),
                PdfTextBlock(357.9, 547.0, 454.1, 776.7, "Acute Tox. 3; H301\nSkin Corr. 1C; H314\n"),
                PdfTextBlock(466.8, 547.0, 529.2, 558.1, ">= 0,0002 - <\n"),
                PdfTextBlock(481.3, 558.5, 514.7, 569.6, "0,0015\n"),
            ],
        )
        doc = PdfDocument(
            file_name="07. HS Coragen 20 SC.pdf",
            pages=[page],
            page_count=1,
            character_count=len(page.text),
            pages_with_text=1,
            processable=True,
            warnings=[],
        )

        items = extract_composition_components(doc)

        self.assertEqual(
            [(item.name, item.cas, item.concentration) for item in items],
            [
                ("Clorantraniliprol", "500008-45-7", ">= 10 - < 20"),
                (
                    "Masa de reacción de 5-cloro-2-metil-2H-isotiazol-3-ona y "
                    "2-metil-2H-isotiazol-3-ona (3:1)",
                    "55965-84-9",
                    ">= 0,0002 - < 0,0015",
                ),
            ],
        )
        self.assertNotIn("613-167-00-5", [item.cas for item in items])

    def test_dow_generic_component_header_extracts_glyphosate_dma(self):
        page_text = (
            "3. COMPOSICIÓN/INFORMACIÓN SOBRE LOS COMPONENTES\n"
            "Naturaleza química: Regulador del crecimiento vegetal\n"
            "Este producto es una mezcla.\n"
            "Componente Número de registro CAS Concentración\n"
            "Glifosato Sal DMA 34494-04-7 50.2%\n"
            "Saldo No disponible 49.8%\n"
            "4. PRIMEROS AUXILIOS\n"
        )
        page = PdfPage(
            page=2,
            text=page_text,
            blocks=[
                PdfTextBlock(
                    79.2, 462.2, 429.7, 476.8,
                    "3. COMPOSICIÓN/INFORMACIÓN SOBRE LOS COMPONENTES\n",
                ),
                PdfTextBlock(
                    79.2, 499.7, 330.6, 522.5,
                    "Naturaleza química: Regulador del crecimiento vegetal\n"
                    "Este producto es una mezcla.\n",
                ),
                PdfTextBlock(
                    79.6, 522.8, 489.9, 545.4,
                    "Componente\nNúmero de registro\nCAS\nConcentración\n",
                ),
                PdfTextBlock(
                    79.2, 573.3, 469.2, 584.4,
                    "Glifosato Sal DMA\n34494-04-7\n50.2%\n",
                ),
                PdfTextBlock(
                    79.2, 598.4, 469.2, 609.5,
                    "Saldo\nNo disponible\n49.8%\n",
                ),
                PdfTextBlock(
                    79.2, 656.1, 206.4, 670.6,
                    "4. PRIMEROS AUXILIOS\n",
                ),
            ],
        )
        doc = PdfDocument(
            file_name="HS Dow.pdf",
            pages=[page],
            page_count=1,
            character_count=len(page_text),
            pages_with_text=1,
            processable=True,
            warnings=[],
        )

        items = extract_composition_components(doc)

        self.assertEqual(
            [(item.name, item.cas, item.concentration) for item in items],
            [("Glifosato Sal DMA", "34494-04-7", "50.2")],
        )

    def test_mayoral_sds_components_are_not_promoted_to_active_ingredients(self):
        self.assertEqual(extract_active_ingredients(self._mayoral_document()), [])


if __name__ == "__main__":
    unittest.main()
