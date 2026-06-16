"""YT↔SC matcher corroboration rule (#43) + the fold projection — guards the 517 union."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))
from match_youtube import is_match, title_sim, TITLE_STRONG, TITLE_WITH_DUR, TITLE_WITH_SCR  # noqa: E402
from fold_orphans import canonical, CANON  # noqa: E402


class TestMatchRule(unittest.TestCase):
    def test_duration_alone_does_NOT_match(self):
        # the exact #43 false-positive class: two ~equal-length sermons, weak title, no scripture
        self.assertFalse(is_match(0.20, False, True))

    def test_strong_title_alone_matches(self):
        self.assertTrue(is_match(TITLE_STRONG, False, False))

    def test_scripture_plus_duration_matches(self):
        self.assertTrue(is_match(0.05, True, True))

    def test_scripture_plus_some_title_matches(self):
        self.assertTrue(is_match(TITLE_WITH_SCR, True, False))

    def test_duration_plus_decent_title_matches(self):
        self.assertTrue(is_match(TITLE_WITH_DUR, False, True))

    def test_no_signal_no_match(self):
        self.assertFalse(is_match(0.10, False, False))


class TestTitleSim(unittest.TestCase):
    def test_identical_high_unrelated_low(self):
        same = title_sim("Image de Dieu | Genèse 1 : 26", "Image de Dieu | Genèse 1 : 26")
        diff = title_sim("Image de Dieu | Genèse 1 : 26", "Prier selon le cœur | Psaume 40")
        self.assertGreater(same, TITLE_STRONG)
        self.assertLess(diff, TITLE_WITH_DUR)


class TestCanonicalProjection(unittest.TestCase):
    def test_projects_to_schema_keeps_provenance_fills_defaults(self):
        out = canonical({"id": "sc-1", "speaker": "David Pelosi",
                         "speaker_provenance": "default-rule", "topics": None})
        self.assertEqual(set(out), set(CANON))                 # exactly the canonical keys
        self.assertEqual(out["speaker_provenance"], "default-rule")
        self.assertEqual(out["topics"], [])                    # None → []
        self.assertIsNone(out["title"])                        # missing → None


if __name__ == "__main__":
    unittest.main()
