import unittest
from types import SimpleNamespace

from src.evidence_presentation import (
    channel_label,
    consolidate_evidence_hits,
    context_label,
    evidence_pages,
    list_label,
    usage_label,
)


def make_hit(*, ingredient="Deltametrina", cas="52918-63-5", source_list="MITIGATE_RISK",
             source_file="10. HS DeltaPoint 2.5 WP.pdf", channel="CAS", page=2,
             criteria="Efectos graves", source_version="2026"):
    entry = SimpleNamespace(
        ingredient=ingredient,
        cas=cas,
        usage="Insecticida · Acaricida",
        criteria=criteria,
        source_list=source_list,
        source_version=source_version,
    )
    return SimpleNamespace(
        entry=entry,
        channel=channel,
        source_file=source_file,
        page=page,
        context="ingrediente activo",
        context_class="ACTIVE",
    )


class EvidencePresentationTests(unittest.TestCase):
    def test_same_entry_found_by_cas_and_name_is_one_card(self):
        cards = consolidate_evidence_hits([
            make_hit(channel="CAS", page=2),
            make_hit(channel="NAME", page=3),
        ])
        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0]["pages"], {2, 3})
        self.assertEqual(len(cards[0]["hit_items"]), 2)

    def test_visually_identical_entries_with_unicode_or_spacing_variants_are_one_card(self):
        cards = consolidate_evidence_hits([
            make_hit(),
            make_hit(
                ingredient="  DELTAMETRINA  ",
                cas=" 52918–63–5 ",
                source_list=" mitigate_risk ",
                source_file="10. HS DeltaPoint 2.5 WP.pdf ",
                channel="NAME",
                page=2,
            ),
        ])
        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0]["ingredient"], "Deltametrina")
        self.assertEqual(cards[0]["pages"], {2})

    def test_distinct_documents_remain_separate_cards(self):
        cards = consolidate_evidence_hits([
            make_hit(source_file="FT.pdf"),
            make_hit(source_file="FDS.pdf"),
        ])
        self.assertEqual(len(cards), 2)

    def test_shared_labels_preserve_current_ui_text(self):
        self.assertEqual(list_label("PROHIBITED"), "RA · Prohibidos")
        self.assertEqual(context_label("ACTIVE"), "Ingrediente activo")
        self.assertEqual(channel_label("NAME"), "Nombre")
        self.assertEqual(
            usage_label("I, A"),
            "Insecticida · Acaricida",
        )

    def test_evidence_pages_uses_best_context_priority(self):
        cards = consolidate_evidence_hits([
            make_hit(channel="CAS", page=5),
            make_hit(channel="NAME", page=2),
        ])
        cards[0]["hit_items"][0].context_class = "REFERENCE_TOXICOLOGY"
        cards[0]["hit_items"][1].context_class = "ACTIVE"
        self.assertEqual(evidence_pages(cards[0]), "2")


if __name__ == "__main__":
    unittest.main()
