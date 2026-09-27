import re
import unittest
from pathlib import Path

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
README = (ROOT / "README.md").read_text(encoding="utf-8")


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

    def test_framework_links_are_consistent_between_app_and_readme(self):
        urls = (
            "https://rspo.org/wp-content/uploads/SPA-2024-RSPO-Principles-and-Criteria-%E2%80%93-Version-4.2-spanish.pdf",
            "https://iscc-system.org/wp-content/uploads/dlm_uploads/2026/03/ISCC-EU-202-2-Agricultural-Biomass-ISCC-Principles-2-6.pdf",
            "https://knowledge.rainforest-alliance.org/docs/es/farming-annex-v14",
        )
        for url in urls:
            with self.subTest(url=url):
                self.assertIn(url, APP)
                self.assertIn(url, README)

    def test_local_base_update_date_matches_interface(self):
        self.assertIn("Última carga de la base local: septiembre de 2026", APP)
        self.assertIn("Última carga de la base local: septiembre de 2026", README)

    def test_readme_documents_no_live_normative_fetch(self):
        self.assertIn("no consulta las páginas en tiempo real", README)
        self.assertIn("no se consultan en tiempo real", README)

    def test_pubchem_is_documented_as_non_decision_reference(self):
        self.assertIn("PubChem", APP)
        self.assertIn("PubChem", README)
        self.assertIn("no participa en la evaluación", README)


if __name__ == "__main__":
    unittest.main()
