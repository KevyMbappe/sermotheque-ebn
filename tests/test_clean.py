"""Unit tests for the conservative ASR cleanup (transcribe.clean_transcript)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))
from transcribe import clean_transcript  # noqa: E402


class TestCleanTranscript(unittest.TestCase):
    def test_fixes_foi(self):
        self.assertEqual(clean_transcript("la confession des fois sur Christ"),
                         "la confession de foi sur Christ")

    def test_fixes_god_persons(self):
        self.assertEqual(clean_transcript("Dieu les Fils a pris chair"), "Dieu le Fils a pris chair")
        self.assertEqual(clean_transcript("selon Dieu les Pères"), "selon Dieu le Père")

    def test_fixes_seigneur(self):
        self.assertEqual(clean_transcript("nous attendons les Seigneurs Jésus"),
                         "nous attendons le Seigneur Jésus")

    # Negative tests — legitimate French must NOT be touched.
    def test_keeps_plusieurs_fois(self):
        self.assertEqual(clean_transcript("nous l'avons dit plusieurs fois"),
                         "nous l'avons dit plusieurs fois")

    def test_keeps_pagan_gods(self):
        self.assertEqual(clean_transcript("les dieux des nations étaient des idoles"),
                         "les dieux des nations étaient des idoles")


if __name__ == "__main__":
    unittest.main()
