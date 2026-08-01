"""Vocabulaire curé des thèmes (#57).

Ces tests verrouillent surtout les pièges rencontrés en construisant le vocabulaire.
Chacun correspond à un rattachement FAUX observé sur les vraies données — le genre
d'erreur qu'une relecture de liste ne voit pas, parce que le résultat a l'air normal.
"""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))

import topics  # noqa: E402
from topics import VOCABULARY, canonicalize, fold, normalize_topics  # noqa: E402


class TestFold(unittest.TestCase):
    def test_strips_accents_and_case(self):
        self.assertEqual(fold("Ézéchiel"), "ezechiel")
        self.assertEqual(fold("PÉCHÉ Originel"), "peche originel")

    def test_unfolds_ligatures(self):
        # La decomposition Unicode ne touche PAS « oe » : sans traitement explicite,
        # « Pacte des oeuvres » ne rencontrait jamais son alias.
        self.assertEqual(fold("œuvres"), "oeuvres")
        self.assertEqual(fold("Sœur"), "soeur")

    def test_none_and_empty(self):
        self.assertEqual(fold(None), "")
        self.assertEqual(fold(""), "")


class TestNoFalsePositives(unittest.TestCase):
    """Les rattachements faux sont pires que les absents : ils mentent en silence."""

    def test_substring_does_not_leak_across_words(self):
        # « soumission » contient « mission », « empechements » contient « peche ».
        self.assertIsNone(canonicalize("Soumission mutuelle"))
        self.assertIsNone(canonicalize("Empêchements"))

    def test_book_names_are_not_topics(self):
        for label in ["Épître aux Hébreux", "Épître de Jacques", "Actes des Apôtres",
                      "Évangile de Luc", "Ézéchiel", "Philippiens", "Tite 2",
                      "Prophétie d'Ézéchiel"]:
            self.assertIsNone(canonicalize(label), label)

    def test_stoplist_is_narrow_enough(self):
        # Un « evangile de » trop large avalait ce vrai theme.
        self.assertEqual(canonicalize("Évangile de la grâce"), "grace")


class TestOrderSensitiveCases(unittest.TestCase):
    """Le specifique doit passer avant le general — l'ordre du vocabulaire est porteur."""

    def test_crainte(self):
        self.assertEqual(canonicalize("Crainte de l'homme"), "crainte_homme")
        self.assertEqual(canonicalize("Crainte des hommes"), "crainte_homme")
        self.assertEqual(canonicalize("Crainte de Dieu"), "crainte_dieu")

    def test_revelation(self):
        self.assertEqual(canonicalize("Révélation progressive"), "hermeneutique")
        self.assertEqual(canonicalize("Révélation de Dieu"), "ecriture")

    def test_fidelite(self):
        self.assertEqual(canonicalize("Fidélité de Dieu"), "attributs")
        self.assertEqual(canonicalize("Fidélité"), "vie_chretienne")

    def test_leadership(self):
        self.assertEqual(canonicalize("Leadership masculin"), "famille")
        self.assertEqual(canonicalize("Leadership serviteur"), "ministeres")

    def test_glorification(self):
        self.assertEqual(canonicalize("Glorification"), "glorification")
        self.assertEqual(canonicalize("Glorification et ascension du Christ"), "christologie")


class TestPlurals(unittest.TestCase):
    def test_trailing_plural_matches(self):
        self.assertEqual(canonicalize("Qualifications des diacres"), "ministeres")
        self.assertEqual(canonicalize("Péchés"), "peche")
        self.assertEqual(canonicalize("Missions"), "mission")

    def test_plural_does_not_create_leaks(self):
        # « s? » ne doit pas ouvrir la porte a des prefixes arbitraires.
        self.assertIsNone(canonicalize("Soumissions"))


class TestSynonymsCollapse(unittest.TestCase):
    """Le probleme d'origine : des formes multiples pour une meme notion."""

    def test_hermeneutique_variants(self):
        for v in ["Herméneutique", "Herméneutique biblique", "Herméneutique christocentrique"]:
            self.assertEqual(canonicalize(v), "hermeneutique", v)

    def test_union_variants(self):
        for v in ["Union avec Christ", "Union à Christ", "Union au Christ"]:
            self.assertEqual(canonicalize(v), "union_christ", v)

    def test_image_de_dieu_variants(self):
        for v in ["Imago Dei", "Image de Dieu", "Image de Dieu (Imago Dei)"]:
            self.assertEqual(canonicalize(v), "imago_dei", v)

    def test_alliance_variants(self):
        for v in ["Théologie des alliances", "Théologie de l'alliance", "Alliance de grâce",
                  "Nouvelle Alliance", "Pacte des œuvres", "Théologie fédérale"]:
            self.assertEqual(canonicalize(v), "alliances", v)


class TestNormalizeTopics(unittest.TestCase):
    def test_dedups_and_follows_vocabulary_order(self):
        got = normalize_topics(["Sanctification", "Sanctification progressive", "Christologie"])
        self.assertEqual(got, ["christologie", "sanctification"])  # ordre du vocabulaire

    def test_unknown_labels_are_dropped_not_guessed(self):
        self.assertEqual(normalize_topics(["Zzz inconnu", "Épître aux Hébreux"]), [])

    def test_empty(self):
        self.assertEqual(normalize_topics(None), [])
        self.assertEqual(normalize_topics([]), [])


class TestVocabularyIntegrity(unittest.TestCase):
    def test_ids_unique(self):
        ids = [c["id"] for c in VOCABULARY]
        self.assertEqual(len(ids), len(set(ids)))

    def test_size_within_the_intended_range(self):
        # La decision d'origine visait un vocabulaire borne (~30-60 termes) : au-dela,
        # ce n'est plus un vocabulaire cure, c'est de nouveau une liste libre.
        self.assertTrue(30 <= len(VOCABULARY) <= 60, len(VOCABULARY))

    def test_every_alias_is_folded_ascii(self):
        # Un accent litteral dans un alias peut etre stocke en NFD et ne jamais matcher.
        for c in VOCABULARY:
            for a in c["aliases"]:
                self.assertEqual(a, fold(a), f"{c['id']}: {a!r} doit etre deja plie")

    def test_every_category_has_a_label(self):
        for c in VOCABULARY:
            self.assertTrue(c["label"].strip(), c["id"])


class TestAgainstCommittedCatalog(unittest.TestCase):
    """Sur les donnees reellement commitees — c'est la que les regressions se voient."""

    @classmethod
    def setUpClass(cls):
        cls.rows = json.loads((ROOT / "data" / "catalog" / "catalog.json").read_text(encoding="utf-8"))

    def test_derived_field_present_on_enriched_rows(self):
        enriched = [r for r in self.rows if r.get("topics")]
        self.assertTrue(enriched)
        for r in enriched:
            self.assertIn("topics_canonical", r, r["id"])

    def test_every_canonical_id_exists_in_the_vocabulary(self):
        known = {c["id"] for c in VOCABULARY}
        for r in self.rows:
            for t in r.get("topics_canonical") or []:
                self.assertIn(t, known, r["id"])

    def test_reproducible_from_the_free_text(self):
        # Le champ est DERIVE : il doit se recalculer a l'identique depuis `topics`.
        for r in self.rows:
            self.assertEqual(r.get("topics_canonical") or [], normalize_topics(r.get("topics")),
                             r["id"])

    def test_coverage_stays_high(self):
        from collections import Counter
        raw = Counter(t for r in self.rows for t in (r.get("topics") or []))
        total = sum(raw.values())
        unmapped = sum(n for l, n in raw.items() if not canonicalize(l))
        self.assertGreater(total, 0)
        # 98% aujourd'hui. Le seuil protege contre une regression du vocabulaire ;
        # le reste est constitue de noms de livres, volontairement exclus.
        self.assertGreaterEqual((total - unmapped) / total, 0.95)

    def test_no_row_is_over_labelled(self):
        # Un sermon range dans 15 categories ne serait plus consultable par theme.
        for r in self.rows:
            self.assertLessEqual(len(r.get("topics_canonical") or []), 12, r["id"])


class TestReportHelpers(unittest.TestCase):
    def test_label_of(self):
        self.assertEqual(topics.label_of("sanctification"), "Sanctification")
        self.assertEqual(topics.label_of("inconnu"), "inconnu")


if __name__ == "__main__":
    unittest.main()
