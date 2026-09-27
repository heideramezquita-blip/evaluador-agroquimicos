"""Exercise the complete PDF-to-evidence rendering path for duplicate cards."""

import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import fitz
from streamlit.testing.v1 import AppTest

from src.engine import analyze


ROOT = Path(__file__).resolve().parents[1]


class StreamlitEvidenceTests(unittest.TestCase):
    def test_deltamethrin_pdf_detected_by_cas_and_name_renders_one_card(self):
        with fitz.open() as document:
            page = document.new_page()
            page.insert_text((50, 70), "Documento sintetico para probar la presentacion de evidencia.")
            page = document.new_page()
            page.insert_text(
                (50, 70),
                "COMPOSICION DEL PRODUCTO\n"
                "Ingrediente activo: Deltametrina.\n"
                "CAS 52918-63-5. Concentracion 2.5 por ciento.\n"
                "Documento sintetico, no es una ficha comercial.",
            )
            payload = document.tobytes()

        filename = "deltametrina-regression.pdf"
        result = analyze([(filename, payload)])
        self.assertEqual({hit.channel for hit in result["evaluation"].hits}, {"CAS", "NAME"})

        upload = SimpleNamespace(name=filename, getvalue=lambda: payload)
        # Supply the uploaded bytes at the widget boundary; use the real PDF
        # reader, detector, evaluation and Streamlit rendering below it.
        with patch("streamlit.file_uploader", return_value=[upload]):
            app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=20).run()
            next(button for button in app.button if button.label == "Evaluar documentos").click().run()

        self.assertEqual(len(app.exception), 0)
        cards = [
            item.value for item in app.markdown
            if '<div class="match-title">Deltametrina</div>' in item.value
        ]
        self.assertEqual(len(cards), 1)
        self.assertEqual(
            [item.label for item in app.expander if item.label.startswith("Ver evidencia documental")],
            ["Ver evidencia documental — Deltametrina"],
        )
        self.assertIn("Riesgo para organismos acuáticos", cards[0])
        self.assertIn("Página(s) más relevante(s):</b> 2", cards[0])
        metrics = {item.label: item.value for item in app.metric}
        self.assertEqual(
            {key: metrics[key] for key in ("PROHIBIDOS", "OBSOLETOS", "MITIGACIÓN")},
            {"PROHIBIDOS": "165", "OBSOLETOS": "24", "MITIGACIÓN": "168"},
        )


if __name__ == "__main__":
    unittest.main()
