"""Enrichment store/writeback (#44) — pure merge logic, offline, no catalog I/O."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))
from enrichment_store import apply, extract  # noqa: E402


class TestEnrichmentStore(unittest.TestCase):
    def test_apply_layers_enrichment_by_id_leaving_structure_intact(self):
        rows = [
            {"id": "sc-1", "title": "T1", "scripture_osis": "Ps.40.1", "topics": [], "summary": None},
            {"id": "sc-2", "title": "T2", "topics": []},
        ]
        store = {"sc-1": {"topics": ["Prière"], "summary": "S", "transcript_ref": "x.txt"}}
        out, merged = apply(rows, store)
        self.assertEqual(merged, 1)
        self.assertEqual(out[0]["topics"], ["Prière"])      # enrichment applied
        self.assertEqual(out[0]["summary"], "S")
        self.assertEqual(out[0]["transcript_ref"], "x.txt")
        self.assertEqual(out[0]["title"], "T1")             # structural untouched
        self.assertEqual(out[0]["scripture_osis"], "Ps.40.1")
        self.assertEqual(out[1]["topics"], [])              # no store entry → unchanged

    def test_store_entry_for_unknown_id_is_ignored(self):
        rows = [{"id": "sc-1", "topics": []}]
        _, merged = apply(rows, {"sc-999": {"topics": ["X"]}})
        self.assertEqual(merged, 0)
        self.assertEqual(rows[0]["topics"], [])

    def test_extract_keeps_only_nonempty_enrichment_fields(self):
        e = {"id": "sc-1", "title": "T", "date": "2026-01-01",        # structural — excluded
             "topics": ["A"], "summary": None, "scripture_refs": [],   # empty — excluded
             "transcript_ref": "x.txt"}                                # kept
        self.assertEqual(set(extract(e)), {"topics", "transcript_ref"})


if __name__ == "__main__":
    unittest.main()
