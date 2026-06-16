#!/usr/bin/env python3
"""
Sermothèque EBN — voiceprint store (#46): id-keyed `data/catalog/voiceprints.json`,
`{ <entry-id>: {model, dim, embedding:[...]} }`.

Audio-derived and one-shot (like the transcripts), so `build_entry` writes it from the same
download. Speaker *attribution* (cosine vs per-speaker centroids → name + provenance) reads
these vectors and is re-runnable, so it is deliberately NOT in this store. Pure stdlib.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STORE = ROOT / "data" / "catalog" / "voiceprints.json"


def load(path=STORE):
    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def save_embedding(eid, vector, *, model="resemblyzer", path=STORE):
    """Upsert one sermon's voiceprint, keyed by entry id. Returns the store."""
    store = load(path)
    store[eid] = {"model": model, "dim": len(vector), "embedding": list(vector)}
    Path(path).write_text(json.dumps(store, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    return store
