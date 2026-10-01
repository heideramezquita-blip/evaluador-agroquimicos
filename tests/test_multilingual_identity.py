import csv
import tempfile
import unittest
from pathlib import Path

from src.context_classifier import ACTIVE, COMPOSITION, classify_context
from src.models import PdfDocument, PdfPage
from src.prohibited_database import ProhibitedDatabase
from src.prohibited_detector import detect_candidates


class MultilingualChemicalIdentityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        data = Path(self.tmp.name)

        with (data / "master_restrictions.csv").open("w", encoding="utf-8", newline="") as target:
            writer = csv.DictWriter(
                target,
                fieldnames=[
                    "source_list", "action", "scope", "ingredient", "cas",
                    "usage", "criteria", "source_code", "source_version", "source_date",
                ],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "source_list": "PROHIBITED",
                    "action": "NO_UTILIZAR",
                    "scope": "",
                    "ingredient": "Tiametoxam",
                    "cas": "153719-23-4",
                    "usage": "I",
                    "criteria": "Efectos graves: ✓",
                    "source_code": "test",
                    "source_version": "test",
                    "source_date": "2026-09-30",
                }
            )

        with (data / "chemical_substances.csv").open("w", encoding="utf-8", newline="") as target:
            writer = csv.DictWriter(
                target,
                fieldnames=[
                    "substance_id", "canonical_name", "canonical_cas",
                    "parent_substance_id", "chemical_form", "source",
                ],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "substance_id": "CAS_153719_23_4",
                    "canonical_name": "Thiamethoxam",
                    "canonical_cas": "153719-23-4",
                    "parent_substance_id": "",
                    "chemical_form": "",
                    "source": "PubChem",
                }
            )

        with (data / "chemical_aliases.csv").open("w", encoding="utf-8", newline="") as target:
            writer = csv.DictWriter(
                target,
                fieldnames=[
                    "substance_id", "canonical_cas", "alias", "language",
                    "alias_type", "source", "confidence", "enabled",
                ],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "substance_id": "CAS_153719_23_4",
                    "canonical_cas": "153719-23-4",
                    "alias": "Thiamethoxam",
                    "language": "en_or_international",
                    "alias_type": "pubchem_title",
                    "source": "PubChem PUG REST",
                    "confidence": "high",
                    "enabled": "true",
                }
            )
            writer.writerow(
                {
                    "substance_id": "CAS_153719_23_4",
                    "canonical_cas": "153719-23-4",
                    "alias": "Cruiser",
                    "language": "und",
                    "alias_type": "candidate_synonym",
                    "source": "PubChem PUG REST",
                    "confidence": "candidate",
                    "enabled": "false",
                }
            )

        self.db = ProhibitedDatabase(data / "master_restrictions.csv")

    def tearDown(self):
        self.tmp.cleanup()

    @staticmethod
    def document(text):
        return PdfDocument(
            "fixture.pdf",
            [PdfPage(1, text)],
            1,
            len(text),
            1,
            True,
        )

    def test_english_pubchem_title_maps_to_same_regulatory_entry(self):
        hits = detect_candidates(
            [self.document("Active substance: Thiamethoxam 250 g/L")],
            [],
            self.db,
        )
        self.assertEqual(len(hits), 1)
        hit = hits[0]
        self.assertEqual(hit.entry.ingredient, "Tiametoxam")
        self.assertEqual(hit.context_class, ACTIVE)
        self.assertEqual(hit.substance_id, "CAS_153719_23_4")
        self.assertEqual(hit.canonical_name, "Thiamethoxam")
        self.assertEqual(hit.alias_type, "pubchem_title")
        self.assertEqual(hit.alias_language, "en_or_international")

    def test_spanish_regulatory_name_remains_supported(self):
        hits = detect_candidates(
            [self.document("Ingrediente activo: Tiametoxam 250 g/L")],
            [],
            self.db,
        )
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].entry.ingredient, "Tiametoxam")

    def test_disabled_candidate_synonym_does_not_match(self):
        hits = detect_candidates(
            [self.document("Product name: Cruiser")],
            [],
            self.db,
        )
        self.assertEqual(hits, [])

    def test_registry_counts_enabled_and_stored_aliases_separately(self):
        self.assertEqual(self.db.identity_registry.substance_count, 1)
        self.assertEqual(self.db.identity_registry.alias_count, 2)
        self.assertEqual(self.db.identity_registry.enabled_alias_count, 1)

    def test_english_identity_headings_are_confirmatory_context(self):
        self.assertEqual(
            classify_context("Chemical name | Thiamethoxam", "Thiamethoxam"),
            COMPOSITION,
        )
        self.assertEqual(
            classify_context("Common name | Thiamethoxam", "Thiamethoxam"),
            COMPOSITION,
        )
        self.assertEqual(
            classify_context("Active substance | Thiamethoxam", "Thiamethoxam"),
            ACTIVE,
        )


if __name__ == "__main__":
    unittest.main()
