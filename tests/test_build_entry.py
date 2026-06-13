"""Integration test for the single entry point (build_entry) with injected fakes.

No network, no API cost, deterministic — the two external steps (transcribe, enrich)
are stubbed, so this exercises the whole compose/assemble path offline.
"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))
from build_entry import build_entry, parse_title  # noqa: E402

FIXTURE = (Path(__file__).resolve().parent / "fixtures" / "sample_transcript.txt").read_text(encoding="utf-8")
SOURCE = {"soundcloud_id": "123",
          "raw_title": "La doctrine de l'incarnation de Christ | Luc 1 : 26 - 38"}
ENRICHMENT = {"summary": "Introduction à l'incarnation.", "topics": ["Incarnation", "Christologie"],
              "primary_scripture": "Luc 1:26-38", "scripture_refs": ["Jean 1:14"],
              "series_hint": "Confession de foi ch.8"}


class TestBuildEntry(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.calls = {}

    def _build(self, source=SOURCE, enrichment=ENRICHMENT):
        def fake_transcribe(src):
            self.calls["transcribe"] = src          # capture: proves it's called with the source
            return FIXTURE
        def fake_enrich(transcript, parsed):
            self.calls["enrich"] = (transcript, parsed)
            return enrichment
        return build_entry(source, transcribe=fake_transcribe, enrich=fake_enrich,
                           transcripts_dir=self.tmp)

    def test_end_to_end_assembly(self):
        e = self._build()
        self.assertEqual(e["id"], "sc-123")
        self.assertEqual(e["source"], "soundcloud")
        # title-derived (deterministic)
        self.assertEqual(e["scripture_osis"], "Luke.1.26-Luke.1.38")
        self.assertEqual(e["title"], "La doctrine de l'incarnation de Christ")
        # enrichment-derived (injected)
        self.assertEqual(e["topics"], ["Incarnation", "Christologie"])
        self.assertEqual(e["summary"], "Introduction à l'incarnation.")
        self.assertEqual(e["series_hint"], "Confession de foi ch.8")
        self.assertEqual(e["scripture_refs"], ["Jean 1:14"])

    def test_transcript_persisted(self):
        e = self._build()
        path = self.tmp / "sc-123.txt"
        self.assertTrue(path.exists())
        self.assertEqual(path.read_text(encoding="utf-8"), FIXTURE)
        self.assertTrue(e["transcript_ref"].endswith("sc-123.txt"))

    def test_steps_actually_invoked(self):
        self._build()
        self.assertEqual(self.calls["transcribe"], SOURCE)
        self.assertEqual(self.calls["enrich"][0], FIXTURE)

    def test_graceful_when_enrichment_empty(self):
        e = self._build(enrichment={})
        self.assertEqual(e["topics"], [])
        self.assertIsNone(e["summary"])
        # primary_scripture falls back to the title-parsed display when the LLM gives nothing
        self.assertEqual(e["primary_scripture"], e["scripture_display"])

    def test_missing_raw_title_raises(self):
        with self.assertRaises(ValueError):
            build_entry({"soundcloud_id": "1"}, transcribe=lambda s: "", enrich=lambda t, p: {})


class TestParseTitle(unittest.TestCase):
    def test_parse_title_speaker_and_series(self):
        p = parse_title("La perfection de la loi | Jacques 1 : 25 (Partie I)")
        self.assertEqual(p["scripture_book"], "Jas")
        self.assertEqual(p["series_part"], 1)


if __name__ == "__main__":
    unittest.main()
