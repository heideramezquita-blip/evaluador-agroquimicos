import unittest

import fitz

from src.cas_extractor import _role
from src.cas_utils import extract_cas_candidates
from src.engine import _identity_basis
from src.context_classifier import (
    ACTIVE,
    COMPOSITION,
    PRODUCT_IDENTITY,
    REFERENCE_LIST,
    DECOMPOSITION,
    INCIDENTAL,
    NEGATED,
    REFERENCE,
    classify_context,
    has_active_marker,
    has_product_identity_marker,
    has_reference_list_marker,
    has_composition_marker,
    has_identity_marker,
)
from src.models import PdfDocument, PdfPage
from src.pdf_reader import read_pdf
from src.prohibited_database import _aliases
from src.text_utils import match_key


class BenchmarkContextPatternsTests(unittest.TestCase):
    def test_parenthesized_active_label_is_recognized(self):
        text = "Ingrediente(s) Activo(s) | Paraquat 200 g/L"
        self.assertTrue(has_active_marker(text))
        self.assertEqual(classify_context(text, "Paraquat"), ACTIVE)

    def test_singular_parenthesized_active_label_is_recognized(self):
        text = "Ingrediente activo(s) | Glifosato 480 g/L"
        self.assertTrue(has_active_marker(text))
        self.assertEqual(classify_context(text, "Glifosato"), ACTIVE)

    def test_iupac_ia_label_is_active_evidence(self):
        text = "Nombre IUPAC (I.A): | Ametrina | 834-12-8"
        self.assertTrue(has_active_marker(text))
        self.assertEqual(_role(text), "active_explicit")
        self.assertEqual(classify_context(text, "Ametrina"), ACTIVE)

    def test_bare_ia_letters_are_not_active_evidence(self):
        self.assertFalse(has_active_marker("Guía de seguridad para aplicación"))
        self.assertEqual(_role("Guía de seguridad para aplicación"), "unknown")

    def test_composition_heading_punctuation_variants_are_recognized(self):
        variants = (
            "COMPOSICIÓN, INFORMACIÓN SOBRE COMPONENTES",
            "COMPOSICIÓN: INFORMACIÓN SOBRE LOS COMPONENTES",
            "Composición: Información sobre los Ingredientes",
            "COMPOSICIÓN / INFORMACIÓN SOBRE LOS INGREDIENTES",
            "COMPOSICIÓN/INFORMACIÓN DE LOS COMPONENTES",
            "3. Composición",
            "COMPOSICIÓN PORCENTUAL/ANÁLISIS GARANTIZADO",
            "COMPOSICIÓN GARANTIZADA",
        )
        for text in variants:
            with self.subTest(text=text):
                self.assertTrue(has_composition_marker(text))
                self.assertTrue(has_identity_marker(text))

    def test_nearby_toxicology_heading_does_not_override_closer_active_label(self):
        context = (
            "INFORMACIÓN TOXICOLÓGICA | Datos generales | Advertencias | "
            "INFORMACIÓN TÉCNICA | Ingrediente activo | Ametrina 480 g/L"
        )
        self.assertEqual(classify_context(context, "Ametrina"), ACTIVE)

    def test_coalesced_toxicology_and_active_labels_prefer_explicit_active(self):
        context = (
            "INFORMACIÓN TOXICOLÓGICA INFORMACIÓN TÉCNICA "
            "Ingrediente activo Ametrina 480 g/L"
        )
        self.assertEqual(classify_context(context, "Ametrina"), ACTIVE)

    def test_reference_remains_reference_when_it_is_local_to_match(self):
        context = "INFORMACIÓN TOXICOLÓGICA | Ametrina | DL50 oral"
        self.assertEqual(classify_context(context, "Ametrina"), REFERENCE)

    def test_negation_same_line_remains_non_supporting(self):
        context = "El producto no contiene Paraquat"
        self.assertEqual(classify_context(context, "Paraquat"), NEGATED)

    def test_decomposition_same_line_remains_non_supporting(self):
        context = "Productos de descomposición: monóxido de carbono"
        self.assertEqual(
            classify_context(context, "monóxido de carbono"),
            DECOMPOSITION,
        )

    def test_web_catalog_product_name_is_incidental_not_product_identity(self):
        context = (
            "NOSOTROS PRODUCTOS CONTÁCTANOS | Ziram 76 | Trecatol WP | "
            "HERBICIDAS HERBICIDAS | Descripción"
        )
        self.assertEqual(classify_context(context, "Ziram"), INCIDENTAL)

    def test_plain_sds_composition_is_not_promoted_to_active(self):
        context = (
            "3. COMPOSICIÓN | Nombre químico | Fipronil | 120068-37-3 | 12 %"
        )
        self.assertEqual(classify_context(context, "Fipronil"), COMPOSITION)

    def test_product_identifier_is_distinct_supporting_context(self):
        context = "1. Identificador del producto | Product name | Thiamethoxam"
        self.assertTrue(has_product_identity_marker(context))
        self.assertEqual(
            classify_context(context, "Thiamethoxam"),
            PRODUCT_IDENTITY,
        )

    def test_prohibited_list_header_is_recognized_as_reference_document_marker(self):
        context = (
            "Anexo 1. Listado de plaguicidas prohibidos | "
            "PLAGUICIDAS PROHIBIDOS Ingrediente activo o grupo Número CAS | "
            "Abamectina 71751-41-2"
        )
        self.assertTrue(has_reference_list_marker(context))



class BenchmarkCasPatternsTests(unittest.TestCase):
    def test_eu_index_suffix_is_not_misread_as_cas(self):
        text = "Número INDEX: 613-088-00-6"
        self.assertEqual(extract_cas_candidates(text), [])

    def test_normal_cas_is_still_detected(self):
        text = "CAS: 91465-08-6"
        self.assertEqual(extract_cas_candidates(text), ["91465-08-6"])



class BenchmarkIdentityBasisTests(unittest.TestCase):
    def _document(self, text):
        return PdfDocument(
            file_name="test.pdf",
            pages=[PdfPage(page=1, text=text)],
            page_count=1,
            character_count=len(text),
            pages_with_text=1,
            processable=True,
            warnings=[],
        )

    def test_bare_composition_heading_does_not_support_clean_no_match(self):
        document = self._document(
            "3. COMPOSICIÓN, INFORMACIÓN SOBRE COMPONENTES | "
            "4. MEDIDAS DE PRIMEROS AUXILIOS"
        )
        self.assertEqual(_identity_basis([document], []), [])

    def test_explicit_active_label_supports_identity_basis(self):
        document = self._document("Ingrediente activo: Sustancia Ejemplo 200 g/L")
        self.assertEqual(
            _identity_basis([document], []),
            ["referencia explícita a ingrediente activo"],
        )


class BenchmarkAliasPatternsTests(unittest.TestCase):
    def _keys(self, name):
        return {match_key(alias) for alias in _aliases(name)}

    def test_positional_qualifier_can_precede_substance(self):
        keys = self._keys("Cihalotrina, lambda")
        self.assertIn("lambda cihalotrina", keys)
        self.assertIn("lambdacihalotrina", keys)

    def test_benzoate_salt_word_order_is_normalized(self):
        keys = self._keys("Benzoato de emamectina")
        self.assertIn("emamectina benzoato", keys)

    def test_hydrochloride_salt_word_order_is_normalized(self):
        keys = self._keys("Clorhidrato de propamocarb")
        self.assertIn("propamocarb clorhidrato", keys)

    def test_paraquat_dichloride_word_order_is_normalized(self):
        keys = self._keys("Dicloruro de paraquat")
        self.assertIn("paraquat dicloruro", keys)

    def test_unrelated_comma_synonym_is_not_reversed_generically(self):
        keys = self._keys("Óxido de propileno, Oxirano")
        self.assertNotIn("oxirano oxido de propileno", keys)


class BenchmarkPdfReaderPatternsTests(unittest.TestCase):
    def test_visual_order_is_used_for_pdf_text(self):
        doc = fitz.open()
        page = doc.new_page()
        # Insert in reverse logical order but place the heading visually above.
        page.insert_text((72, 200), "Paraquat 200 g/L")
        page.insert_text((72, 100), "Ingredientes Activos")
        payload = doc.tobytes()
        doc.close()

        result = read_pdf(payload, "visual-order.pdf")
        text = result.pages[0].text
        self.assertLess(text.index("Ingredientes Activos"), text.index("Paraquat 200 g/L"))

    def test_repeated_footer_only_document_is_unprocessable(self):
        footer = (
            "EMPRESA EJEMPLO S.A.S. | contacto@example.com | "
            "Documento generado para información del producto"
        )
        doc = fitz.open()
        for _ in range(3):
            page = doc.new_page()
            page.insert_text((72, 700), footer)
        payload = doc.tobytes()
        doc.close()

        result = read_pdf(payload, "scan-with-footer.pdf")
        self.assertFalse(result.processable)
        self.assertTrue(
            any("texto repetido" in warning for warning in result.warnings)
        )


if __name__ == "__main__":
    unittest.main()
