"""Voiceprint store + build_entry capture (#46) — offline, no torch/audio."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))
import voiceprint_store  # noqa: E402
from build_entry import build_entry  # noqa: E402


class TestVoiceprintStore(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.store = self.tmp / "voiceprints.json"

    def test_save_and_load_roundtrip(self):
        voiceprint_store.save_embedding("sc-1", [0.1, 0.2, 0.3], path=self.store)
        voiceprint_store.save_embedding("yt-2", [0.4, 0.5], model="resemblyzer", path=self.store)
        s = voiceprint_store.load(self.store)
        self.assertEqual(s["sc-1"]["embedding"], [0.1, 0.2, 0.3])
        self.assertEqual(s["sc-1"]["dim"], 3)
        self.assertEqual(s["yt-2"]["model"], "resemblyzer")

    def test_build_entry_persists_embedding_from_transcriber(self):
        # The real transcriber attaches result["embedding"] (voiceprint from the same audio);
        # build_entry should write it to the voiceprint store, keyed by id.
        rich = {"text": "x", "vtt": "", "segments": [], "language": "fr", "embedding": [0.9, 0.8]}
        build_entry({"soundcloud_id": "123", "raw_title": "T | Luc 1 : 1"},
                    transcribe=lambda s: rich, enrich=lambda t, p: {},
                    transcripts_dir=self.tmp, voiceprints_path=self.store)
        self.assertEqual(voiceprint_store.load(self.store)["sc-123"]["embedding"], [0.9, 0.8])

    def test_no_embedding_no_store_write(self):
        build_entry({"soundcloud_id": "123", "raw_title": "T | Luc 1 : 1"},
                    transcribe=lambda s: "plain text", enrich=lambda t, p: {},
                    transcripts_dir=self.tmp, voiceprints_path=self.store)
        self.assertFalse(self.store.exists())


if __name__ == "__main__":
    unittest.main()
