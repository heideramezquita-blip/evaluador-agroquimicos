import unittest
from pathlib import Path

from src.normative_sources import (
    WHO_EN,
    WHO_ES,
    WHO_PDF,
    MONTREAL_PROTOCOL,
    ROTTERDAM_ANNEX_III,
    ROTTERDAM_PIC,
    STOCKHOLM_POP_LIST,
    STOCKHOLM_ANNEX_A,
    STOCKHOLM_ANNEX_B,
    reference_blocks_markdown,
)

ROOT = Path(__file__).resolve().parents[1]


class NormativeSourcesTests(unittest.TestCase):
    def test_streamlit_reference_blocks_include_each_official_link_once(self):
        blocks = reference_blocks_markdown()
        for url in (
            WHO_EN, WHO_ES, WHO_PDF, MONTREAL_PROTOCOL, ROTTERDAM_ANNEX_III, ROTTERDAM_PIC,
            STOCKHOLM_POP_LIST, STOCKHOLM_ANNEX_A, STOCKHOLM_ANNEX_B,
        ):
            with self.subTest(url=url):
                self.assertEqual(blocks.count(url), 1)
        for required in (
            "2019 edition", "publicada en 2020", "peligrosidad aguda",
            "Ia, Ib, II, III y U", "distinta del SGA",
            "Protocolo de Montreal", "agotan la capa de ozono",
            "no equivale a una prohibición universal", "anexos A, B y C",
        ):
            with self.subTest(text=required):
                self.assertIn(required, blocks)

    def test_app_shows_reference_blocks_and_short_interpretation_once(self):
        app = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertEqual(app.count("st.markdown(reference_blocks_markdown())"), 1)
        self.assertEqual(app.count("with st.expander('Cómo interpretar los criterios de las listas')"), 1)
        self.assertIn("OMS Ia/Ib:", app)
        self.assertIn("SGA 1A/1B:", app)
        self.assertIn("procedimiento de consentimiento fundamentado previo", reference_blocks_markdown())
        glossary = app.split("with st.expander('Cómo interpretar los criterios de las listas'):", 1)[1]
        for required in (
            "Ia significa extremadamente peligroso e Ib, altamente peligroso",
            "CMR: carcinogenicidad, mutagenicidad y toxicidad reproductiva",
            "consentimiento fundamentado previo (PIC) en el comercio internacional",
            "eliminación (anexo A)",
            "restricción (anexo B)",
            "reducción de liberaciones no intencionales (anexo C)",
            "Efectos graves:",
            "Mitigación de riesgos:",
            "requiere medidas adicionales para reducir riesgos específicos",
            "no significa por sí sola que el plaguicida esté prohibido",
            "en esta aplicación, sus listas son una referencia complementaria",
        ):
            with self.subTest(text=required):
                self.assertIn(required, glossary)

    def test_readme_contains_each_official_link_once_and_explains_no_live_import(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for url in (
            WHO_EN, WHO_ES, WHO_PDF, MONTREAL_PROTOCOL, ROTTERDAM_ANNEX_III, ROTTERDAM_PIC,
            STOCKHOLM_POP_LIST, STOCKHOLM_ANNEX_A, STOCKHOLM_ANNEX_B,
        ):
            with self.subTest(url=url):
                self.assertEqual(readme.count(url), 1)
        self.assertIn("no consulta las páginas en tiempo real", readme)
        self.assertIn("no importa automáticamente esas listas", readme)
        self.assertIn("OMS Ia / Ib", readme)
        self.assertIn("SGA 1A / 1B", readme)
        self.assertIn("Rainforest Alliance", readme)

    def test_normative_source_module_has_no_network_dependency(self):
        source = (ROOT / "src" / "normative_sources.py").read_text(encoding="utf-8")
        self.assertNotIn("requests", source)
        self.assertNotIn("urllib", source)
        self.assertNotIn("httpx", source)


if __name__ == "__main__":
    unittest.main()
