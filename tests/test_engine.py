import unittest
from pathlib import Path
from unittest.mock import patch

from src.engine import analyze
from src.rules import STATUS_MITIGATION, STATUS_NO_CAS, STATUS_NO_MATCH, STATUS_NO_USE, STATUS_REVIEW


MASTER = Path(__file__).resolve().parents[1] / "data" / "master_restrictions.csv"


class EngineTests(unittest.TestCase):
    def test_manual_invalid_cas_is_rejected(self):
        result = analyze(
            [],
            manual_cas_text="167-00-5",
            master_path=MASTER,
            enable_name_fallback=False,
        )
        self.assertEqual(result["evaluation"].status, STATUS_NO_CAS)
        self.assertEqual(result["manual_valid"], [])
        self.assertEqual(result["manual_invalid"], ["167-00-5"])

    def test_manual_prohibited_requires_active_confirmation(self):
        result = analyze(
            [],
            manual_cas_text="153719-23-4",
            manual_active_confirmed=False,
            master_path=MASTER,
            enable_name_fallback=False,
        )
        self.assertEqual(result["evaluation"].status, STATUS_REVIEW)

        result_confirmed = analyze(
            [],
            manual_cas_text="153719-23-4",
            manual_active_confirmed=True,
            master_path=MASTER,
            enable_name_fallback=False,
        )
        self.assertEqual(result_confirmed["evaluation"].status, STATUS_NO_USE)

    def test_manual_nonrestricted_cas_uses_same_pipeline(self):
        result = analyze(
            [],
            manual_cas_text="2061933-85-3",
            master_path=MASTER,
            enable_name_fallback=False,
        )
        self.assertEqual(result["evaluation"].status, STATUS_NO_MATCH)
        self.assertEqual([r.cas for r in result["evaluation"].cas_records], ["2061933-85-3"])

    def test_multiple_manual_cas_are_normalized_and_deduplicated(self):
        result = analyze(
            [],
            manual_cas_text="52918-63-5; 52918635; 2061933-85-3",
            manual_active_confirmed=True,
            master_path=MASTER,
            enable_name_fallback=False,
        )
        self.assertEqual(result["evaluation"].status, STATUS_MITIGATION)
        self.assertEqual(
            {r.cas for r in result["evaluation"].cas_records},
            {"52918-63-5", "2061933-85-3"},
        )

    @patch("src.engine.consultar_pubchem")
    @patch("src.engine.extract_explicit_active_names")
    @patch("src.engine.read_pdf")
    def test_name_fallback_runs_only_when_no_automatic_cas(
        self,
        mock_read_pdf,
        mock_active_names,
        mock_pubchem,
    ):
        from src.models import PdfDocument, PdfPage

        mock_read_pdf.return_value = PdfDocument(
            file_name="ft.pdf",
            pages=[PdfPage(page=1, text="Ingrediente activo: Isocycloseram")],
            page_count=1,
            character_count=40,
            pages_with_text=1,
            processable=True,
        )
        mock_active_names.return_value = [{
            "name": "Isocycloseram",
            "source_file": "ft.pdf",
            "page": 1,
            "evidence": "Ingrediente activo",
        }]
        mock_pubchem.return_value = {
            "estado": "identificado",
            "cid": 87323565,
            "cas": "2061933-85-3",
            "cas_candidatos": ["2061933-85-3"],
            "mensaje": "ok",
        }

        result = analyze(
            [("ft.pdf", b"dummy")],
            master_path=MASTER,
            enable_name_fallback=True,
        )
        self.assertEqual(result["evaluation"].status, STATUS_NO_MATCH)
        self.assertEqual([r.cas for r in result["evaluation"].cas_records], ["2061933-85-3"])
        mock_pubchem.assert_called_once_with("Isocycloseram")

    @patch("src.engine.consultar_pubchem")
    @patch("src.engine.extract_explicit_active_names")
    @patch("src.engine.read_pdf")
    def test_name_fallback_is_skipped_when_document_has_cas(
        self,
        mock_read_pdf,
        mock_active_names,
        mock_pubchem,
    ):
        from src.models import PdfDocument, PdfPage

        mock_read_pdf.return_value = PdfDocument(
            file_name="hs.pdf",
            pages=[PdfPage(page=1, text="Componente 2061933-85-3")],
            page_count=1,
            character_count=80,
            pages_with_text=1,
            processable=True,
        )
        mock_active_names.return_value = [{
            "name": "Isocycloseram",
            "source_file": "hs.pdf",
            "page": 1,
            "evidence": "Ingrediente activo",
        }]

        result = analyze(
            [("hs.pdf", b"dummy")],
            master_path=MASTER,
            enable_name_fallback=True,
        )
        self.assertEqual(result["evaluation"].status, STATUS_NO_MATCH)
        mock_pubchem.assert_not_called()


if __name__ == "__main__":
    unittest.main()
