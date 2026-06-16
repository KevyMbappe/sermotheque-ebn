"""Tier-A fingerprint — feature extraction + nearest-centroid LOO (offline, synthetic)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))
from fingerprint import extract, _matrix, leave_one_out  # noqa: E402


class TestFingerprint(unittest.TestCase):
    def test_extract_pulls_text_raw_and_vtt_features(self):
        e = extract("le le la de et que qui", raw="confession des fois en Dieu les Fils",
                    vtt="WEBVTT\n\n00:00:00.000 --> 00:01:00.000\nx")
        self.assertGreater(e["fw:le"], 0)                 # function words
        self.assertGreater(e["artifact_per_1k"], 0)        # accent artifacts from raw
        self.assertIsNotNone(e["words_per_sec"])           # cadence from vtt

    def test_missing_raw_and_vtt_leave_features_none(self):
        e = extract("le la de et")
        self.assertIsNone(e["artifact_per_1k"])
        self.assertIsNone(e["words_per_sec"])

    def test_loo_separates_two_clear_styles(self):
        # two synthetic speakers with opposite function-word profiles → perfectly separable
        A = [{"fw:le": 0.9, "fw:la": 0.1, "ttr": 0.5} for _ in range(3)]
        B = [{"fw:le": 0.1, "fw:la": 0.9, "ttr": 0.5} for _ in range(3)]
        rows, _ = _matrix(A + B)
        labels = ["A"] * 3 + ["B"] * 3
        preds = leave_one_out(rows, labels)
        correct = sum(labels[i] == preds[i][0] for i in range(len(labels)) if preds[i][0])
        self.assertEqual(correct, 6)


if __name__ == "__main__":
    unittest.main()
