"""Audio speaker attribution (#49) — pure vector/ladder logic, offline, synthetic embeddings."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))
import speaker_id as S  # noqa: E402


class TestVectorMath(unittest.TestCase):
    def test_cosine_identical_and_orthogonal(self):
        self.assertAlmostEqual(S.cosine([1, 0, 0], [2, 0, 0]), 1.0)
        self.assertAlmostEqual(S.cosine([1, 0, 0], [0, 1, 0]), 0.0)

    def test_centroid_is_unit_mean_direction(self):
        c = S.centroid([[1, 0, 0], [0, 1, 0]])
        self.assertAlmostEqual(c[0], c[1])                 # symmetric
        self.assertAlmostEqual(sum(x * x for x in c), 1.0)  # unit length

    def test_classify_picks_nearest(self):
        cents = {"A": [1, 0, 0], "B": [0, 1, 0]}
        spk, sim, margin = S.classify([0.9, 0.1, 0], cents)
        self.assertEqual(spk, "A")
        self.assertGreater(margin, 0)


def _vp(vec):
    return {"model": "t", "dim": len(vec), "embedding": vec}


class TestAttribution(unittest.TestCase):
    def setUp(self):
        # Three robust speakers (≥2 title examples each) + one thin (1 example). 4-dim so each
        # speaker is orthogonal and the fixtures don't cross-contaminate.
        self.rows = [
            {"id": "a1", "speaker": "Ann", "speaker_provenance": "title"},
            {"id": "a2", "speaker": "Ann", "speaker_provenance": "title"},
            {"id": "b1", "speaker": "Bob", "speaker_provenance": "title"},
            {"id": "b2", "speaker": "Bob", "speaker_provenance": "title"},
            {"id": "d1", "speaker": "Dan", "speaker_provenance": "title"},
            {"id": "d2", "speaker": "Dan", "speaker_provenance": "title"},
            {"id": "c1", "speaker": "Cid", "speaker_provenance": "title"},   # thin: 1 example
            {"id": "g_default", "speaker": "Ann", "speaker_provenance": "default-rule"},  # really Bob
            {"id": "g_blank", "speaker": None, "speaker_provenance": None},               # really Ann
            {"id": "g_title", "speaker": "Dan", "speaker_provenance": "title"},           # title Dan, audio Bob
        ]
        self.vps = {
            "a1": _vp([1, 0, 0, 0]), "a2": _vp([0.98, 0.02, 0, 0]),
            "b1": _vp([0, 1, 0, 0]), "b2": _vp([0.02, 0.98, 0, 0]),
            "d1": _vp([0, 0, 0, 1]), "d2": _vp([0, 0, 0.02, 0.98]),
            "c1": _vp([0, 0, 1, 0]),
            "g_default": _vp([0, 1, 0, 0]),  # matches Bob → over default-rule → reassign
            "g_blank": _vp([1, 0, 0, 0]),    # matches Ann → over blank → reassign
            "g_title": _vp([0, 1, 0, 0]),    # matches Bob but row is title=Dan → title-conflict
        }

    def _decisions(self):
        recs = S.attribute(self.rows, self.vps, overrides={})
        return {r["id"]: r["decision"] for r in recs}

    def test_reassigns_over_default_rule_and_blank(self):
        d = self._decisions()
        self.assertEqual(d["g_default"], "reassign")
        self.assertEqual(d["g_blank"], "reassign")

    def test_title_label_is_flagged_not_overridden(self):
        self.assertEqual(self._decisions()["g_title"], "title-conflict")

    def test_thin_centroid_match_is_review(self):
        # A blank sermon that looks like Cid (1 example) must not auto-apply.
        self.rows.append({"id": "g_cid", "speaker": None, "speaker_provenance": None})
        self.vps["g_cid"] = _vp([0, 0, 1])
        self.assertEqual(self._decisions()["g_cid"], "review")

    def test_store_excludes_review_and_conflicts(self):
        recs = S.attribute(self.rows, self.vps, overrides={})
        store = S.to_store(recs)
        self.assertIn("g_default", store)
        self.assertEqual(store["g_default"]["provenance"], "audio-fingerprint")
        self.assertNotIn("g_title", store)        # title kept, not stored
        self.assertEqual(store["g_default"]["speaker"], "Bob")

    def test_human_override_wins(self):
        recs = S.attribute(self.rows, self.vps, overrides={"g_default": "Zoe"})
        store = S.to_store(recs)
        self.assertEqual(store["g_default"], {"speaker": "Zoe", "provenance": "human"})


class TestPanelExclusion(unittest.TestCase):
    def test_panel_title_detected(self):
        self.assertTrue(S.is_panel("10th Good News Conference: Brian Borgman, Don Currin, Joel Favre and David Pelosi"))

    def test_single_speaker_conference_talk_is_not_panel(self):
        self.assertFalse(S.is_panel("Encountered by God | Professor David Pelosi | CBN8 Paris 2024"))

    def test_normal_sermon_title_is_not_panel(self):
        self.assertFalse(S.is_panel("La Piété Avec Contentement | Pr. David Pelosi"))

    def test_panel_excluded_from_ground_truth(self):
        rows = [{"id": "p1", "speaker": "David Pelosi", "speaker_provenance": "title",
                 "raw_title": "Conference: A, B and David Pelosi"},
                {"id": "s1", "speaker": "David Pelosi", "speaker_provenance": "title",
                 "raw_title": "Sermon | Pr. David Pelosi"}]
        vps = {"p1": _vp([1, 0, 0]), "s1": _vp([1, 0, 0])}
        gt = S.ground_truth(rows, vps, overrides={})
        self.assertEqual([i for i, _ in gt["David Pelosi"]], ["s1"])   # panel p1 excluded


class TestSeriesPrior(unittest.TestCase):
    def test_cohesive_series_seeds_ground_truth_and_flags_outlier(self):
        # A series owned by one preacher: 3 cohesive members + 1 outlier (a different voice that week).
        spk = next(iter(S.SERIES_SPEAKER)); owner = S.SERIES_SPEAKER[spk]
        rows = [{"id": f"x{i}", "series_name": spk, "raw_title": f"Sermon {i}"} for i in range(4)]
        vps = {"x0": _vp([1, 0, 0]), "x1": _vp([0.99, 0.01, 0]), "x2": _vp([0.98, 0.02, 0]),
               "x3": _vp([0, 1, 0])}   # x3 is a clear outlier (different voice)
        labeled, outliers = S.series_labels(rows, vps)
        kept = {i for i, _ in labeled[owner]}
        self.assertEqual(kept, {"x0", "x1", "x2"})
        self.assertEqual([o[0] for o in outliers], ["x3"])

    def test_title_label_beats_series_prior_for_same_id(self):
        spk = next(iter(S.SERIES_SPEAKER))
        rows = [{"id": "z", "series_name": spk, "raw_title": "S", "speaker": "Someone Else",
                 "speaker_provenance": "title"}]
        gt = S.ground_truth(rows, {"z": _vp([1, 0, 0])}, overrides={})
        self.assertIn("Someone Else", gt)                       # title wins
        self.assertNotIn(S.SERIES_SPEAKER[spk], gt)


class TestLadderApply(unittest.TestCase):
    def test_audio_overrides_default_rule_not_title(self):
        rows = [{"id": "x", "speaker": "Ann", "speaker_provenance": "default-rule"},
                {"id": "y", "speaker": "Ann", "speaker_provenance": "title"}]
        store = {"x": {"speaker": "Bob", "provenance": "audio-fingerprint"},
                 "y": {"speaker": "Bob", "provenance": "audio-fingerprint"}}
        out, changed = S.apply(rows, store)
        self.assertEqual(changed, 1)
        self.assertEqual(out[0]["speaker"], "Bob")          # default-rule overridden
        self.assertEqual(out[0]["speaker_provenance"], "audio-fingerprint")
        self.assertEqual(out[1]["speaker"], "Ann")          # title kept
        self.assertEqual(out[1]["speaker_provenance"], "title")

    def test_human_overrides_title(self):
        rows = [{"id": "x", "speaker": "Ann", "speaker_provenance": "title"}]
        out, changed = S.apply(rows, {"x": {"speaker": "Zoe", "provenance": "human"}})
        self.assertEqual(changed, 1)
        self.assertEqual(out[0]["speaker"], "Zoe")


if __name__ == "__main__":
    unittest.main()
