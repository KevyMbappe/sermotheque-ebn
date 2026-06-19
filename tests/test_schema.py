"""Frozen canonical record contract (#53) — conformance + drift guard, offline."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))
import schema                       # noqa: E402
from fold_orphans import CANON      # noqa: E402
from enrichment_store import ENRICHMENT_FIELDS  # noqa: E402


class TestContractDriftGuard(unittest.TestCase):
    def test_pipeline_fieldlists_exactly_cover_the_schema(self):
        # The two places that WRITE a catalog row (structural fold + enrichment writeback) must
        # together produce exactly the frozen field set — no field escapes the contract.
        written = set(CANON) | set(ENRICHMENT_FIELDS)
        self.assertEqual(written, set(schema.FIELDS),
                         f"drift: only-in-code={written - set(schema.FIELDS)}, "
                         f"only-in-schema={set(schema.FIELDS) - written}")

    def test_structural_fields_are_required(self):
        # Everything in CANON is structural → must be required on every row.
        for k in CANON:
            self.assertIn(k, schema.REQUIRED, f"{k} is structural but not required")


class TestValidator(unittest.TestCase):
    def test_minimal_valid_row(self):
        row = {k: None for k in schema.REQUIRED}
        row.update(topics=[], translation_candidates=[], media={}, is_conference=False)
        self.assertEqual(schema.validate(row), [])

    def test_missing_required_field_flagged(self):
        row = {k: None for k in schema.REQUIRED if k != "id"}
        self.assertTrue(any("id" in e for e in schema.validate(row)))

    def test_wrong_type_flagged(self):
        row = {k: None for k in schema.REQUIRED}
        row["topics"] = "not-a-list"
        self.assertTrue(any("topics" in e for e in schema.validate(row)))

    def test_unknown_field_flagged(self):
        row = {k: None for k in schema.REQUIRED}
        row["surprise"] = 1
        self.assertTrue(any("surprise" in e for e in schema.validate(row)))

    def test_array_item_type_checked(self):
        row = {k: None for k in schema.REQUIRED}
        row["topics"] = ["ok", 5]      # second item wrong type
        self.assertTrue(any("topics[1]" in e for e in schema.validate(row)))

    def test_number_field_accepts_float(self):
        row = {k: None for k in schema.REQUIRED}
        row["youtube_match"] = 1.8     # match score is a number, not an object
        self.assertEqual(schema.validate(row), [])


class TestLiveCatalogConforms(unittest.TestCase):
    def test_every_catalog_row_is_valid(self):
        rows = json.loads((ROOT / "data" / "catalog" / "catalog.json").read_text(encoding="utf-8"))
        bad = {r.get("id"): schema.validate(r) for r in rows if schema.validate(r)}
        self.assertEqual(bad, {}, f"{len(bad)} rows violate the frozen contract")


if __name__ == "__main__":
    unittest.main()
