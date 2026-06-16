"""Integration test for the single entry point (build_entry) with injected fakes.

No network, no API cost, deterministic — the two external steps (transcribe, enrich)
are stubbed, so this exercises the whole compose/assemble path offline.
"""
import json
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

    RICH = {"text": FIXTURE, "vtt": "WEBVTT\n\n00:00.000 --> 00:02.000\nAu commencement.\n",
            "segments": [{"start": 0.0, "end": 2.0, "text": "Au commencement.",
                          "words": [{"word": "Au", "start": 0.0, "end": 0.4}], "no_speech_prob": 0.01}],
            "language": "fr"}

    def test_vtt_persisted_but_segments_off_by_default(self):
        # Default keeps txt + vtt only; the heavy word-level .json is opt-in (#42).
        e = build_entry(SOURCE, transcribe=lambda s: self.RICH,
                        enrich=lambda t, p: ENRICHMENT, transcripts_dir=self.tmp)
        self.assertEqual((self.tmp / "sc-123.txt").read_text(encoding="utf-8"), FIXTURE)
        self.assertEqual((self.tmp / "sc-123.vtt").read_text(encoding="utf-8"), self.RICH["vtt"])
        self.assertTrue(e["captions_ref"].endswith("sc-123.vtt"))
        self.assertFalse((self.tmp / "sc-123.json").exists())
        self.assertIsNone(e["segments_ref"])

    def test_segments_persisted_when_opted_in(self):
        e = build_entry(SOURCE, transcribe=lambda s: self.RICH, enrich=lambda t, p: ENRICHMENT,
                        transcripts_dir=self.tmp, persist_segments=True)
        loaded = json.loads((self.tmp / "sc-123.json").read_text(encoding="utf-8"))
        self.assertEqual(loaded["segments"][0]["words"][0]["word"], "Au")
        self.assertTrue(e["segments_ref"].endswith("sc-123.json"))

    def test_raw_transcript_persisted_when_provided(self):
        rich = {**self.RICH, "text_raw": "confession des fois en Dieu les Fils"}  # uncleaned
        e = build_entry(SOURCE, transcribe=lambda s: rich, enrich=lambda t, p: ENRICHMENT,
                        transcripts_dir=self.tmp)
        self.assertEqual((self.tmp / "sc-123.raw.txt").read_text(encoding="utf-8"),
                         "confession des fois en Dieu les Fils")
        self.assertTrue(e["raw_ref"].endswith("sc-123.raw.txt"))

    def test_string_transcriber_leaves_timestamp_refs_empty(self):
        e = self._build()  # fake returns a plain string
        self.assertIsNone(e["captions_ref"])
        self.assertIsNone(e["segments_ref"])
        self.assertIsNone(e["raw_ref"])

    def test_date_falls_back_to_source_upload_date(self):
        # Title has no date prefix; YouTube's upload_date (YYYYMMDD) should fill it.
        src = {"youtube_id": "X", "raw_title": "Prier | Psaume 40 : 1 - 17", "upload_date": "20260607"}
        e = build_entry(src, transcribe=lambda s: "", enrich=lambda t, p: {})
        self.assertEqual(e["date"], "2026-06-07")

    def test_progress_callback_fires_each_phase(self):
        seen = []
        build_entry(SOURCE, transcribe=lambda s: FIXTURE, enrich=lambda t, p: {},
                    on_progress=seen.append, transcripts_dir=self.tmp)
        self.assertEqual(seen, ["parse", "transcribe", "enrich", "persist", "done"])

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
