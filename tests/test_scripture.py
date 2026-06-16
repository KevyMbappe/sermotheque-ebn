"""Unit tests for the parsing primitives (scripture.py)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))
from scripture import (fold, parse_scripture, parse_speaker, parse_part,  # noqa: E402
                       resolve_speaker, speaker_provenance, DEFAULT_SPEAKER)


def osis(title):
    s = parse_scripture(fold(title), title)
    return s["osis"] if s else None


class TestScripture(unittest.TestCase):
    def test_simple_range(self):
        self.assertEqual(osis("La doctrine | Luc 1 : 26 - 38"), "Luke.1.26-Luke.1.38")

    def test_cross_chapter(self):
        self.assertEqual(osis("Image de Dieu | Genèse 1 : 26 - 2 : 3"), "Gen.1.26-Gen.2.3")

    def test_abbreviated_numbered_book(self):
        self.assertEqual(osis("Noël | 1 Tim 3 : 14 - 16"), "1Tim.3.14-1Tim.3.16")

    def test_english_flag(self):
        s = parse_scripture(fold("The Triumph of Mercy | James 2:12-13"), "James 2:12-13")
        self.assertEqual(s["osis"], "Jas.2.12-Jas.2.13")
        self.assertTrue(s["is_english"])

    def test_no_reference(self):
        self.assertIsNone(parse_scripture(fold("Introduction au panorama"), "Introduction au panorama"))


class TestSpeakerAndPart(unittest.TestCase):
    def test_speaker_parenthetical_pr(self):
        self.assertEqual(parse_speaker("Dédicace | 1 Rois 8:27 (Pr. David Pelosi)"), "David Pelosi")

    def test_speaker_trailing_known_name(self):
        self.assertEqual(parse_speaker("Une bénédiction | Genèse 32:24-32 Joël Beeke"), "Joël Beeke")

    def test_series_marker_is_not_speaker(self):
        self.assertIsNone(parse_speaker("Confession de foi ( Chapitre IV, partie 9 ) | Genèse 1"))

    def test_part_roman_and_lecon(self):
        self.assertEqual(parse_part("La perfection | Jacques 1:25 (Partie I)"), 1)
        self.assertEqual(parse_part("Leçon n°10"), 10)
        self.assertEqual(parse_part("Galates Ch. 2 v 11 à 16 (2)"), 2)

    def test_default_speaker_rule(self):
        # untagged sermon → the regular preacher
        self.assertEqual(resolve_speaker("Image de Dieu | Genèse 1:26"), DEFAULT_SPEAKER)
        # explicit guest named in the title wins
        self.assertEqual(resolve_speaker("La grâce souveraine (Pr. Joël Beeke)"), "Joël Beeke")
        # conference / English left unattributed (likely a guest, don't mis-credit the pastor)
        self.assertIsNone(resolve_speaker("Good News Conference 2024", is_conference=True))
        self.assertIsNone(resolve_speaker("The witness of the Spirit | John 3", is_english=True))

    def test_speaker_provenance_marks_how_speaker_was_decided(self):
        self.assertEqual(speaker_provenance("Image de Dieu | Genèse 1"), "default-rule")
        self.assertEqual(speaker_provenance("La grâce (Pr. Joël Beeke)"), "title")
        self.assertIsNone(speaker_provenance("Good News Conference 2024", is_conference=True))


if __name__ == "__main__":
    unittest.main()
