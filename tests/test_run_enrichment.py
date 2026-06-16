"""Enrichment runner — pure target-selection + source-building (offline, no network)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))
from run_enrichment import select_targets, source_for  # noqa: E402

ROWS = [
    {"id": "sc-1", "source": "soundcloud", "raw_title": "A", "date": "2026-06-07",
     "media": {"soundcloud_id": "1"}},
    {"id": "sc-2", "source": "soundcloud", "raw_title": "B", "media": {"soundcloud_id": "2"}},
    {"id": "yt-1", "source": "youtube", "raw_title": "C", "media": {"youtube_id": "abc"}},
]


class TestSelectTargets(unittest.TestCase):
    def test_filters_by_source(self):
        got = [r["id"] for r in select_targets(ROWS, set(), source="soundcloud")]
        self.assertEqual(got, ["sc-1", "sc-2"])

    def test_resume_skips_already_enriched(self):
        got = [r["id"] for r in select_targets(ROWS, {"sc-1"}, source="soundcloud")]
        self.assertEqual(got, ["sc-2"])

    def test_explicit_ids_and_limit(self):
        self.assertEqual([r["id"] for r in select_targets(ROWS, set(), source="all", ids=["yt-1"])], ["yt-1"])
        self.assertEqual(len(select_targets(ROWS, set(), source="all", limit=1)), 1)


class TestSourceFor(unittest.TestCase):
    def test_youtube_url_derived_and_date_passed(self):
        s = source_for(ROWS[2], {})
        self.assertEqual(s["youtube_url"], "https://www.youtube.com/watch?v=abc")

    def test_soundcloud_url_from_map(self):
        s = source_for(ROWS[0], {"1": "https://soundcloud.com/ebn-paris/a"})
        self.assertEqual(s["soundcloud_url"], "https://soundcloud.com/ebn-paris/a")
        self.assertEqual(s["upload_date"], "20260607")  # date → YYYYMMDD for the date fallback


if __name__ == "__main__":
    unittest.main()
