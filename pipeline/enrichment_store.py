#!/usr/bin/env python3
"""
Sermothèque EBN — enrichment store + writeback (decision #44).

`build.py` regenerates `catalog.json` from raw (parse→match→fold→cluster), so any
enrichment written directly into it — the expensive ASR+LLM output (topics, summary,
scripture refs, transcript/caption refs) — is WIPED on the next rebuild. So enrichment
lives in a separate id-keyed store (`data/catalog/enrichment.json`), and a **writeback**
step merges it back onto the freshly-rebuilt structural catalog. Pure stdlib.

Flow:
  • the full enrichment pass calls `save_entry(build_entry_result, model=...)` per sermon;
  • `build.py` runs `writeback()` as its final step, re-applying the store onto the catalog
    (and regenerating catalog.csv). A rebuild therefore preserves enrichment.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CAT = ROOT / "data" / "catalog" / "catalog.json"
STORE = ROOT / "data" / "catalog" / "enrichment.json"

# The fields produced by enrichment (build_entry output) that must survive a structural
# rebuild. Everything else on a catalog row is structural (re-derived from title/inventory).
ENRICHMENT_FIELDS = ("topics", "summary", "primary_scripture", "scripture_refs",
                     "series_hint", "speaker", "transcript_ref", "captions_ref", "segments_ref")


def load_store(path=STORE):
    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def extract(entry: dict) -> dict:
    """Pull just the (non-empty) enrichment fields out of a build_entry output dict."""
    return {k: entry[k] for k in ENRICHMENT_FIELDS if entry.get(k) not in (None, [], "")}


def save_entry(entry: dict, *, model=None, path=STORE) -> dict:
    """Upsert one build_entry result into the store, keyed by entry id. Returns the store."""
    store = load_store(path)
    rec = extract(entry)
    if model:
        rec["_model"] = model
    store[entry["id"]] = rec
    Path(path).write_text(json.dumps(store, ensure_ascii=False, indent=2, sort_keys=True),
                          encoding="utf-8")
    return store


def apply(rows: list, store: dict):
    """Pure merge: layer the store's enrichment onto catalog rows (by id). Structural
    fields are untouched; ids not in the store are left alone. Returns (rows, merged_count)."""
    merged = 0
    for r in rows:
        rec = store.get(r.get("id"))
        if not rec:
            continue
        for k in ENRICHMENT_FIELDS:
            if k in rec:
                r[k] = rec[k]
        merged += 1
    return rows, merged


def writeback(catalog_path=CAT, store_path=STORE) -> int:
    """Merge the enrichment store onto catalog.json and regenerate catalog.csv."""
    rows = json.loads(Path(catalog_path).read_text(encoding="utf-8"))
    rows, merged = apply(rows, load_store(store_path))
    Path(catalog_path).write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    from cluster_series import write_csv      # keep the flattened export (topics column) in sync
    write_csv(rows)
    return merged


def main():
    n = writeback()
    print(f"  enrichment written back onto {n} catalog rows (store: {len(load_store())} entries)")


if __name__ == "__main__":
    main()
