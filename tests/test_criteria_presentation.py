import ast
import unittest
from pathlib import Path

from src.criteria_presentation import interpret_criterion, interpret_criteria

ROOT = Path(__file__).resolve().parents[1]


class CriteriaPresentationTests(unittest.TestCase):
    def test_oms_ia_is_acute_toxicity_not_sga(self):
        item = interpret_criterion("Toxicidad aguda: 1A")
        self.assertEqual(item.label, "Toxicidad aguda · OMS Ia")
        self.assertIn("extremadamente peligroso", item.explanation)
        self.assertNotIn("SGA", item.label)
        self.assertTrue(item.ra_hhp_criterion)

    def test_oms_ib_is_acute_toxicity_not_sga(self):
        item = interpret_criterion("Toxicidad aguda: 1B")
        self.assertEqual(item.label, "Toxicidad aguda · OMS Ib")
        self.assertIn("altamente peligroso", item.explanation)
        self.assertNotIn("SGA", item.label)
        self.assertTrue(item.ra_hhp_criterion)

    def test_sga_carcinogenicity_1b_keeps_hazard_class(self):
        item = interpret_criterion("Carcinogenicidad: GHS 1B")
        self.assertEqual(item.label, "Carcinogenicidad · SGA 1B")
        self.assertIn("Se presume que causa cáncer", item.explanation)
        self.assertTrue(item.ra_hhp_criterion)

    def test_sga_reproductive_toxicity_1b_keeps_hazard_class(self):
        item = interpret_criterion("Toxicidad reproductiva: GHS 1B")
        self.assertEqual(item.label, "Toxicidad reproductiva · SGA 1B")
        self.assertIn("Se presume que es tóxico para la reproducción", item.explanation)
        self.assertTrue(item.ra_hhp_criterion)

    def test_sga_mutagenicity_1b_keeps_hazard_class(self):
        item = interpret_criterion("Mutagenicidad: GHS 1B")
        self.assertEqual(item.label, "Mutagenicidad · SGA 1B")
        self.assertIn("mutaciones hereditarias", item.explanation)
        self.assertTrue(item.ra_hhp_criterion)

    def test_other_sga_hazard_class_is_not_mapped_to_ra_cmr(self):
        item = interpret_criterion("Sensibilización cutánea: GHS 1A")
        self.assertEqual(item.label, "Sensibilización cutánea · SGA 1A")
        self.assertFalse(item.ra_hhp_criterion)
        self.assertIn("no se interpreta como carcinogenicidad", item.explanation)

    def test_sga_category_without_hazard_class_stays_unresolved(self):
        item = interpret_criterion("GHS 1B")
        self.assertEqual(item.label, "SGA 1B · clase de peligro no indicada")
        self.assertIsNone(item.hazard_class)
        self.assertFalse(item.ra_hhp_criterion)
        self.assertIn("no infiere esa clase", item.explanation)

    def test_source_marker_does_not_invent_exact_sga_subcategory(self):
        item = interpret_criterion("Toxicidad reproductiva: ✓")
        self.assertEqual(item.label, "Toxicidad reproductiva · SGA 1A/1B")
        self.assertEqual(item.category, "1A/1B")
        self.assertIn("no especifica", item.explanation)

    def test_sga_input_is_displayed_as_sga(self):
        item = interpret_criterion("Carcinogenicidad: SGA 1B")
        self.assertEqual(item.label, "Carcinogenicidad · SGA 1B")
        self.assertEqual(item.system, "SGA")

    def test_non_ra_sga_category_does_not_become_ra_criterion(self):
        item = interpret_criterion("Carcinogenicidad: GHS 1B", source_list="MITIGATE_RISK")
        self.assertFalse(item.ra_hhp_criterion)

    def test_criteria_interpreter_expands_each_convention_code(self):
        items = interpret_criteria("Convenciones internacionales: R, E")
        self.assertEqual(
            [item.label for item in items],
            ["Consentimiento fundamentado previo · Convenio de Rotterdam", "Contaminante orgánico persistente · Convenio de Estocolmo"],
        )

    def test_montreal_is_labeled_as_ozone_layer_criterion(self):
        items = interpret_criteria("Convenciones internacionales: M")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].label, "Capa de ozono · Protocolo de Montreal")
        self.assertIn("agotan la capa de ozono", items[0].explanation)

    def test_mitigation_markers_are_human_readable(self):
        items = interpret_criteria("EPP; Riesgo acuático; Polinizadores", "MITIGATE_RISK")
        self.assertEqual(
            [item.label for item in items],
            [
                "Protección personal de nivel superior (EPP)",
                "Riesgo para organismos acuáticos",
                "Riesgo para polinizadores",
            ],
        )

    def test_global_reference_metrics_remain_in_results_ui(self):
        app = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn("result['prohibited_specific_count']+result['prohibited_group_count']", app)
        self.assertIn("c2.metric('OBSOLETOS',result['obsolete_count'])", app)
        self.assertIn("c3.metric('MITIGACIÓN',result['mitigation_count'])", app)

    def test_actual_master_displays_acute_who_context(self):
        import csv
        with (ROOT / "data" / "master_restrictions.csv").open(encoding="utf-8", newline="") as source:
            row = next(item for item in csv.DictReader(source) if item["ingredient"] == "Abamectina")
        item = interpret_criteria(row["criteria"], row["source_list"])[0]
        self.assertEqual(item.label, "Toxicidad aguda · OMS Ib")

    def test_actual_master_cmr_marker_does_not_claim_exact_subcategory(self):
        import csv
        with (ROOT / "data" / "master_restrictions.csv").open(encoding="utf-8", newline="") as source:
            row = next(item for item in csv.DictReader(source) if item["ingredient"] == "Clorpirifos")
        item = interpret_criteria(row["criteria"], row["source_list"])[0]
        self.assertEqual(item.label, "Toxicidad reproductiva · SGA 1A/1B")
        self.assertNotIn("SGA 1B", item.label)

    def test_app_uses_presentation_layer_for_evidence(self):
        app = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn("from src.criteria_presentation import interpret_criteria", app)
        self.assertIn("signals=interpret_criteria(g.get('criteria',''),g['source_list'])", app)

    def test_severe_effects_has_short_rainforest_alliance_definition(self):
        item = interpret_criterion("Efectos graves: ✓")
        self.assertEqual(item.label, "Efectos graves")
        self.assertIn("alta incidencia", item.explanation)
        self.assertIn("irreversibles", item.explanation)
        self.assertTrue(item.ra_hhp_criterion)

    def test_severe_effects_interpretation_is_shown_with_each_evidence_card(self):
        app = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn("criterion_summary_html(g)", app)
        self.assertIn("with st.expander('Cómo interpretar los criterios de las listas')", app)
        glossary = app.split("with st.expander('Cómo interpretar los criterios de las listas'):", 1)[1]
        self.assertIn("**Efectos graves:**", glossary)
        self.assertEqual(glossary.count("**Efectos graves:**"), 1)
        self.assertIn("alta incidencia", (ROOT / "src" / "criteria_presentation.py").read_text(encoding="utf-8"))

    def test_evidence_cards_are_consolidated_across_detection_channels(self):
        app = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn("from src.evidence_presentation import consolidate_evidence_hits", app)
        self.assertIn("for g in consolidate_evidence_hits(ev.hits):", app)

    def test_presentation_module_has_no_network_dependencies(self):
        source = (ROOT / "src" / "criteria_presentation.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        self.assertFalse(imported.intersection({"requests", "httpx", "urllib", "socket"}))


if __name__ == "__main__":
    unittest.main()
