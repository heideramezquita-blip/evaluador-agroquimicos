import re
import unittest
from pathlib import Path

from src.normative_sources import (
    ISCC_EU_202_2,
    LOCAL_BASE_LOAD_DATE,
    MONTREAL_PROTOCOL,
    RA_FARMING_ANNEX,
    ROTTERDAM_ANNEX_III,
    ROTTERDAM_PIC,
    RSPO_PNC_2024_ES,
    STOCKHOLM_ANNEX_A,
    STOCKHOLM_ANNEX_B,
    STOCKHOLM_POP_LIST,
    WHO_EN,
    WHO_ES,
    WHO_PDF,
    reference_blocks_markdown,
    standards_scope_markdown,
)
from src.rules import (
    STATUS_DOCUMENT_REVIEW,
    STATUS_IDENTITY_REVIEW,
    STATUS_MATCH_REVIEW,
    STATUS_MITIGATION,
    STATUS_NO_MATCH,
    STATUS_NO_USE,
    STATUS_NO_USE_RSPO,
    STATUS_OBSOLETE,
    STATUS_RA_PROHIBITED,
)


ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
UI_HELPERS = (ROOT / "src" / "ui_helpers.py").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")
STANDARDS_SCOPE = standards_scope_markdown()
REFERENCE_BLOCKS = reference_blocks_markdown()
DATA_README = (ROOT / "data" / "README.md").read_text(encoding="utf-8")


class DocumentationConsistencyTests(unittest.TestCase):
    def test_all_user_facing_statuses_are_documented_verbatim(self):
        statuses = (
            STATUS_NO_USE,
            STATUS_NO_USE_RSPO,
            STATUS_RA_PROHIBITED,
            STATUS_OBSOLETE,
            STATUS_MITIGATION,
            STATUS_MATCH_REVIEW,
            STATUS_DOCUMENT_REVIEW,
            STATUS_IDENTITY_REVIEW,
            STATUS_NO_MATCH,
        )
        for status in statuses:
            with self.subTest(status=status):
                self.assertIn(status, README)

    def test_document_input_contract_matches_streamlit_uploader(self):
        self.assertRegex(
            APP,
            r"st\.file_uploader\([^\n]+type=\['pdf'\]",
        )
        self.assertIn("uno o varios archivos **PDF**", README)
        self.assertIn("Solo se aceptan archivos PDF", README)
        self.assertIn("FT", README)
        self.assertIn("FDS/HS", README)

    def test_manual_cas_contract_and_example_are_documented(self):
        self.assertIn("Introducir CAS manualmente · opcional", APP)
        self.assertIn("4685-14-7", APP)
        self.assertIn("4685-14-7", README)
        self.assertIn("ingrediente activo", README)
        self.assertIn("Sin esa confirmación", README)

    def test_scanned_document_limitation_is_documented(self):
        self.assertIn("REVISIÓN DOCUMENTAL", README)
        self.assertIn("No hay OCR integrado", README)
        self.assertIn("texto extraíble", README)

    def test_detection_mechanisms_are_documented_without_overclaiming(self):
        for required in (
            "números CAS",
            "nombre",
            "reglas de grupo",
            "checksum",
            "no es un reconocimiento químico abierto o universal",
        ):
            with self.subTest(required=required):
                self.assertIn(required, README)

    def test_glossary_concepts_visible_in_app_are_also_in_readme(self):
        concepts = (
            "OMS Ia/Ib",
            "SGA 1A/1B",
            "Protocolo de Montreal",
            "Rotterdam",
            "Estocolmo",
            "Efectos graves",
            "Mitigación de riesgos",
            "Rainforest Alliance",
        )
        for concept in concepts:
            with self.subTest(concept=concept):
                self.assertIn(concept, APP)
                self.assertIn(concept, README)

    def test_framework_links_are_consistent_between_interface_source_and_readme(self):
        for url in (RSPO_PNC_2024_ES, ISCC_EU_202_2, RA_FARMING_ANNEX):
            with self.subTest(url=url):
                self.assertIn(url, STANDARDS_SCOPE)
                self.assertIn(url, README)

    def test_informational_reference_links_are_consistent_with_readme(self):
        urls = (
            WHO_EN,
            WHO_ES,
            WHO_PDF,
            MONTREAL_PROTOCOL,
            ROTTERDAM_ANNEX_III,
            ROTTERDAM_PIC,
            STOCKHOLM_POP_LIST,
            STOCKHOLM_ANNEX_A,
            STOCKHOLM_ANNEX_B,
        )
        for url in urls:
            with self.subTest(url=url):
                self.assertIn(url, REFERENCE_BLOCKS)
                self.assertIn(url, README)

    def test_group_entries_are_documented_as_rows_without_specific_cas(self):
        self.assertIn("sin CAS específico", DATA_README)
        self.assertNotIn("CAS \u0060varios\u0060", DATA_README)

    def test_local_base_update_date_matches_interface_source(self):
        marker = f"Última carga de la base local: {LOCAL_BASE_LOAD_DATE}"
        self.assertIn(marker, STANDARDS_SCOPE)
        self.assertIn(marker, README)

    def test_result_section_order_is_documented(self):
        self.assertLess(
            APP.index("Evidencia relevante"),
            APP.index("Identidad documental detectada"),
        )
        self.assertIn(
            "primero la sección **Evidencia relevante**",
            README,
        )

    def test_readme_architecture_matches_current_modules(self):
        for module in (
            "src/active_ingredient_extractor.py",
            "src/composition_extractor.py",
            "src/evidence_presentation.py",
            "src/ui_helpers.py",
            "src/ui_styles.py",
        ):
            with self.subTest(module=module):
                self.assertIn(module, README)

    def test_readme_documents_no_live_normative_fetch(self):
        self.assertIn("no consulta las páginas en tiempo real", README)
        self.assertIn("no se consultan en tiempo real", README)

    def test_pubchem_is_documented_as_non_decision_reference(self):
        self.assertIn("pubchem.ncbi.nlm.nih.gov", UI_HELPERS)
        self.assertIn("PubChem", README)
        self.assertIn("no participa en la evaluación", README)


if __name__ == "__main__":
    unittest.main()
