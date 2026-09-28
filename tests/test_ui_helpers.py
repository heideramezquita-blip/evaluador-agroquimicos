import unittest
from types import SimpleNamespace

from src.rules import (
    STATUS_DOCUMENT_REVIEW,
    STATUS_IDENTITY_REVIEW,
    STATUS_MITIGATION,
    STATUS_MITIGATION_REVIEW,
    STATUS_NO_MATCH,
    STATUS_PROHIBITED_REVIEW,
    STATUS_RA_PROHIBITED,
)
from src.ui_helpers import (
    cas_html,
    comparison_basis_summary,
    composition_items_not_already_active,
    pubchem_url,
    result_visual,
    screening_identity_summary,
    table_html,
)


class UiHelpersTests(unittest.TestCase):
    def test_result_colors_distinguish_success_and_identity_review(self):
        self.assertEqual(result_visual(STATUS_NO_MATCH), ("result-green", "✓"))
        self.assertEqual(
            result_visual(STATUS_IDENTITY_REVIEW),
            ("result-purple", "🔎"),
        )
        self.assertEqual(
            result_visual(STATUS_DOCUMENT_REVIEW),
            ("result-yellow", "📄"),
        )

    def test_result_colors_distinguish_prohibited_review_from_mitigation_review(self):
        self.assertEqual(
            result_visual(STATUS_PROHIBITED_REVIEW),
            ("result-red-review", "⚠️"),
        )
        self.assertEqual(
            result_visual(STATUS_RA_PROHIBITED),
            ("result-red-review", "⚠️"),
        )
        self.assertEqual(
            result_visual(STATUS_MITIGATION),
            ("result-pink", "⚠️"),
        )
        self.assertEqual(
            result_visual(STATUS_MITIGATION_REVIEW),
            ("result-pink", "⚠️"),
        )

    def test_red_priority_visuals_remain_above_mitigation(self):
        self.assertEqual(
            result_visual(STATUS_RA_PROHIBITED),
            ("result-red-review", "⚠️"),
        )
        self.assertNotEqual(
            result_visual(STATUS_RA_PROHIBITED)[0],
            result_visual(STATUS_MITIGATION)[0],
        )

    def test_screening_identity_summary_includes_structured_composition(self):
        summary = screening_identity_summary(
            {
                "active_ingredients": [],
                "composition_components": [
                    {"name": "Imazapic", "cas": "104098-48-8"},
                    {"name": "Isopropylamine", "cas": "75-31-0"},
                    {"name": "Imazapyr", "cas": "81334-34-1"},
                ],
                "document_cas": [
                    "104098-48-8",
                    "75-31-0",
                    "81334-34-1",
                ],
                "manual_cas": [],
            }
        )
        self.assertEqual(
            summary,
            "Componentes de composición evaluados: "
            "Imazapic (CAS 104098-48-8); "
            "Isopropylamine (CAS 75-31-0); "
            "Imazapyr (CAS 81334-34-1)",
        )

    def test_screening_identity_summary_pairs_confirmed_active_cas(self):
        summary = screening_identity_summary(
            {
                "active_ingredients": [
                    {"name": "Gentamicin sulphate", "cas": "1405-41-0"},
                    {
                        "name": "Oxytetracycline hydrochloride",
                        "cas": "2058-46-0",
                    },
                ],
                "document_cas": ["1405-41-0", "2058-46-0"],
                "manual_cas": [],
            }
        )
        self.assertEqual(
            summary,
            "Ingredientes activos evaluados: "
            "Gentamicin sulphate (CAS 1405-41-0); "
            "Oxytetracycline hydrochloride (CAS 2058-46-0)",
        )

    def test_screening_identity_summary_falls_back_to_contextual_cas(self):
        self.assertEqual(
            screening_identity_summary(
                {
                    "active_ingredients": [],
                    "document_cas": ["1405-41-0", "2058-46-0"],
                    "manual_cas": [],
                }
            ),
            "CAS evaluados: 1405-41-0; 2058-46-0",
        )

    def test_comparison_basis_prefers_confirmed_active_identity(self):
        summary = comparison_basis_summary(
            {
                "screening_identity": {
                    "active_ingredients": [
                        {"name": "Glifosato", "cas": ""},
                    ],
                    "composition_components": [],
                    "document_cas": [],
                    "manual_cas": [],
                },
                "display_hits": [],
            }
        )
        self.assertEqual(summary, "Ingrediente activo evaluado: Glifosato")

    def test_comparison_basis_prefers_targeted_screening_over_auxiliary_identity(self):
        summary = comparison_basis_summary(
            {
                "targeted_screening": {
                    "documents_processable": 1,
                    "entries_screened": 357,
                    "manual_cas_valid": 0,
                },
                "screening_identity": {
                    "active_ingredients": [
                        {"name": "Identidad auxiliar", "cas": ""},
                    ],
                    "composition_components": [],
                    "document_cas": [],
                    "manual_cas": [],
                },
                "display_hits": [],
            }
        )
        self.assertEqual(
            summary,
            "Tamizaje dirigido: 357 entradas normativas · "
            "1 documento(s) con texto extraíble",
        )
        self.assertNotIn("Identidad auxiliar", summary)

    def test_comparison_basis_review_uses_exact_cas_without_overclaiming_active_role(self):
        hit = SimpleNamespace(
            channel="CAS",
            context_class="UNCERTAIN",
            strength="validated_cas",
            matched_value="138261-41-3",
            entry=SimpleNamespace(
                ingredient="Imidacloprid",
                cas="138261-41-3",
            ),
        )
        summary = comparison_basis_summary(
            {
                "screening_identity": {
                    "active_ingredients": [],
                    "composition_components": [],
                    "document_cas": [],
                    "manual_cas": [],
                },
                "display_hits": [hit],
            }
        )
        self.assertEqual(
            summary,
            "CAS evaluado: 138261-41-3 (Imidacloprid)",
        )
        self.assertNotIn("Ingrediente activo evaluado", summary)

    def test_comparison_basis_prefers_contextual_cas_over_combustion_name_hit(self):
        hit = SimpleNamespace(
            channel="NAME",
            context_class="DECOMPOSITION_COMBUSTION",
            strength="exact_name",
            matched_value="Cianuro de hidrógeno",
            entry=SimpleNamespace(
                ingredient="Cianuro de hidrógeno",
                cas="74-90-8",
                is_group=False,
            ),
        )
        summary = comparison_basis_summary(
            {
                "screening_identity": {
                    "active_ingredients": [],
                    "composition_components": [],
                    "document_cas": ["500008-45-7", "55965-84-9"],
                    "manual_cas": [],
                },
                "display_hits": [],
                "all_hits": [hit],
            }
        )
        self.assertEqual(
            summary,
            "CAS evaluados: 500008-45-7; 55965-84-9",
        )
        self.assertNotIn("Cianuro de hidrógeno", summary)

    def test_comparison_basis_never_promotes_non_supporting_nominal_hit(self):
        hit = SimpleNamespace(
            channel="NAME",
            context_class="DECOMPOSITION_COMBUSTION",
            strength="exact_name",
            matched_value="Cianuro de hidrógeno",
            entry=SimpleNamespace(
                ingredient="Cianuro de hidrógeno",
                cas="74-90-8",
                is_group=False,
            ),
        )
        summary = comparison_basis_summary(
            {
                "screening_identity": {
                    "active_ingredients": [],
                    "composition_components": [],
                    "document_cas": [],
                    "manual_cas": [],
                },
                "display_hits": [],
                "all_hits": [hit],
            }
        )
        self.assertEqual(summary, "")

    def test_comparison_basis_group_review_names_reference_group(self):
        hit = SimpleNamespace(
            channel="GROUP_NAME",
            context_class="UNCERTAIN",
            strength="group_candidate",
            matched_value="glufosinato",
            entry=SimpleNamespace(
                ingredient="Sales e isómeros de glufosinato de amonio",
                cas="",
                is_group=True,
            ),
        )
        summary = comparison_basis_summary(
            {
                "screening_identity": {
                    "active_ingredients": [],
                    "composition_components": [],
                    "document_cas": [],
                    "manual_cas": [],
                },
                "display_hits": [hit],
            }
        )
        self.assertEqual(
            summary,
            "Sustancia/grupo evaluado: "
            "Sales e isómeros de glufosinato de amonio",
        )

    def test_comparison_basis_nominal_review_names_specific_substance(self):
        hit = SimpleNamespace(
            channel="NAME",
            context_class="UNCERTAIN",
            strength="exact_name",
            matched_value="Bifentrina",
            entry=SimpleNamespace(
                ingredient="Bifentrina",
                cas="82657-04-3",
                is_group=False,
            ),
        )
        summary = comparison_basis_summary(
            {
                "screening_identity": {
                    "active_ingredients": [],
                    "composition_components": [],
                    "document_cas": [],
                    "manual_cas": [],
                },
                "display_hits": [hit],
            }
        )
        self.assertEqual(summary, "Sustancia evaluada: Bifentrina")

    def test_pubchem_link_requires_valid_cas(self):
        self.assertEqual(
            pubchem_url("52918-63-5"),
            "https://pubchem.ncbi.nlm.nih.gov/#query=52918-63-5",
        )
        self.assertEqual(pubchem_url("not-a-cas"), "")

    def test_cas_html_escapes_non_link_values(self):
        self.assertEqual(cas_html("<script>"), "&lt;script&gt;")

    def test_table_html_escapes_regular_cells_and_links_valid_cas(self):
        html = table_html(
            [
                {
                    "Sustancia": "<b>Deltametrina</b>",
                    "CAS": "52918-63-5",
                }
            ]
        )
        self.assertIn("&lt;b&gt;Deltametrina&lt;/b&gt;", html)
        self.assertIn("pubchem.ncbi.nlm.nih.gov", html)

    def test_composition_filter_hides_rows_already_confirmed_as_active(self):
        active = [
            SimpleNamespace(name="Deltametrina", cas="52918-63-5"),
        ]
        composition = [
            SimpleNamespace(name="Deltametrina", cas="52918-63-5"),
            SimpleNamespace(name="Solvente ejemplo", cas="123-45-6"),
        ]
        filtered = composition_items_not_already_active(active, composition)
        self.assertEqual([item.name for item in filtered], ["Solvente ejemplo"])


if __name__ == "__main__":
    unittest.main()
