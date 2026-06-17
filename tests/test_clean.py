"""Unit tests for the conservative ASR cleanup (transcribe.clean_transcript)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))
from transcribe import clean_transcript, detect_language, _looks_garbage  # noqa: E402


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


class TestDetectLanguage(unittest.TestCase):
    FR = ("Nous sommes ici en train de considérer la lettre de la liberté et l'objectif "
          "de cette lettre, c'était de protéger l'Église qui est dans le monde pour la gloire de Dieu.")
    EN = ("We are here to consider the letter of liberty and the purpose of this letter was "
          "to protect the church that is in the world for the glory of God and his people.")

    def test_detects_french(self):
        self.assertEqual(detect_language(self.FR), "fr")

    def test_detects_english(self):
        self.assertEqual(detect_language(self.EN), "en")

    def test_french_text_opening_with_english_word(self):
        # The exact failure that fooled Whisper's 30s detector (yt-Tqu-GLCEgbA, #48).
        self.assertEqual(detect_language("Thank you. " + self.FR), "fr")

    def test_too_little_text_is_unclear(self):
        self.assertIsNone(detect_language("Amen."))


class TestLooksGarbage(unittest.TestCase):
    def test_real_transcript_is_not_garbage(self):
        self.assertFalse(_looks_garbage(TestDetectLanguage.FR))

    def test_asr_silence_is_garbage(self):
        # English audio decoded as French collapses to '...' / '!' (yt-HOjW63LMfhQ, #48).
        self.assertTrue(_looks_garbage("...\n\n...\n!\n \n!\n\n...\n \n" * 50))

    def test_empty_is_garbage(self):
        self.assertTrue(_looks_garbage(""))


if __name__ == "__main__":
    unittest.main()
