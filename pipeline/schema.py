#!/usr/bin/env python3
"""
Sermothèque EBN — the FROZEN canonical record contract (decision #53).

One sermon = one row in `data/catalog/catalog.json`. Two pipelines write it (the catalog-build
steps write the STRUCTURAL fields; the enrichment writeback adds the ENRICHMENT fields), and it is
the contract every downstream consumer reads — first of all the WordPress import. Until now its
shape lived implicitly in two hand-maintained lists (`fold_orphans.CANON` + `enrichment_store.
ENRICHMENT_FIELDS`); this module makes it explicit, validates the catalog against it, and emits a
formal JSON Schema (`data/catalog/sermon.schema.json`) for external tools.

Pure stdlib — the validator is a few type checks, no `jsonschema` dependency. A drift guard
(tested) asserts the two pipeline field-lists exactly cover this schema, so the contract can't
silently diverge from what the code writes.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CAT = ROOT / "data" / "catalog" / "catalog.json"
SCHEMA_OUT = ROOT / "data" / "catalog" / "sermon.schema.json"

# Field spec: name -> (json types, required-on-every-row?, item-type for arrays).
# `required` fields are STRUCTURAL (present on all 517 rows). The rest are ENRICHMENT — present
# only once a sermon has been enriched, so they're optional but, when present, must match the type.
_STR, _INT, _NUM, _BOOL, _OBJ, _ARR = "string", "integer", "number", "boolean", "object", "array"

FIELDS = {
    # --- structural (required on every row) ---
    "id":                  (_STR,  True,  None),
    "source":              (_STR,  True,  None),   # "soundcloud" | "youtube"
    "raw_title":           (_STR,  True,  None),
    "title":               (_STR,  True,  None),
    "language":            (_STR,  True,  None),   # "fr" | "en" (audio-detected, #48)
    "date":                (_STR,  True,  None),   # "YYYY-MM-DD" or null
    "audio_duration":      (_INT,  True,  None),
    "video_duration":      (_INT,  True,  None),
    "speaker":             (_STR,  True,  None),
    "speaker_provenance":  (_STR,  True,  None),   # human|title|audio-fingerprint|default-rule|null
    "series_id":           (_STR,  True,  None),
    "series_name":         (_STR,  True,  None),
    "series_part":         (_INT,  True,  None),
    "series_order":        (_INT,  True,  None),
    "scripture_osis":      (_STR,  True,  None),
    "scripture_display":   (_STR,  True,  None),
    "scripture_book":      (_STR,  True,  None),
    "scripture_chapter":   (_INT,  True,  None),
    "scripture_confident": (_BOOL, True,  None),
    "kind":                (_STR,  True,  None),   # sermon|teaching|qa|teaching_or_qa
    "is_conference":       (_BOOL, True,  None),
    "media":               (_OBJ,  True,  None),   # {soundcloud_id, youtube_id, *_url}
    "youtube_match":       (_NUM,  True,  None),   # corroborated match score to a YouTube video (#43), or null
    "translation_candidates": (_ARR, True, _OBJ),
    "topics":              (_ARR,  True,  _STR),
    "summary":             (_STR,  True,  None),
    "transcript_ref":      (_STR,  True,  None),
    # --- enrichment (optional; present once enriched, then type-checked) ---
    "description":         (_STR,  False, None),
    "invitation":          (_STR,  False, None),
    "key_points":          (_ARR,  False, _STR),
    "chapters":            (_ARR,  False, _OBJ),   # [{title, t}]
    "references":          (_ARR,  False, _STR),
    "key_quotes":          (_ARR,  False, _OBJ),   # [{text, t}]
    "questions":           (_ARR,  False, _STR),
    "primary_scripture":   (_STR,  False, None),
    "scripture_refs":      (_ARR,  False, _STR),
    "series_hint":         (_STR,  False, None),
    "raw_ref":             (_STR,  False, None),
    "captions_ref":        (_STR,  False, None),
    "segments_ref":        (_STR,  False, None),
}

REQUIRED = [k for k, (_, req, _i) in FIELDS.items() if req]
_PY = {_STR: str, _INT: int, _NUM: (int, float), _BOOL: bool, _OBJ: dict, _ARR: list}


def _type_ok(value, json_type):
    if value is None:
        return True                       # every field is nullable (missing data → null)
    if json_type in (_INT, _NUM):         # bool is a subclass of int in Python — exclude it
        return isinstance(value, _PY[json_type]) and not isinstance(value, bool)
    return isinstance(value, _PY[json_type])


def validate(row: dict) -> list:
    """Return a list of human-readable contract violations for one catalog row ([] = valid)."""
    errs = []
    for k in REQUIRED:
        if k not in row:
            errs.append(f"missing required field '{k}'")
    for k, v in row.items():
        if k not in FIELDS:
            errs.append(f"unknown field '{k}' (not in the frozen contract)")
            continue
        json_type, _req, item = FIELDS[k]
        if not _type_ok(v, json_type):
            errs.append(f"'{k}' should be {json_type}, got {type(v).__name__}")
        elif item and isinstance(v, list):
            for i, el in enumerate(v):
                if not _type_ok(el, item):
                    errs.append(f"'{k}[{i}]' should be {item}, got {type(el).__name__}")
    return errs


def json_schema() -> dict:
    """The contract as a JSON Schema (draft 2020-12) — for the WP import and external consumers."""
    props = {}
    for k, (json_type, _req, item) in FIELDS.items():
        prop = {"type": [json_type, "null"]}
        if item:
            prop["items"] = {"type": [item, "null"]}
        props[k] = prop
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://eglisebonnenouvelle.com/schemas/sermon.json",
        "title": "Sermothèque EBN — canonical sermon record",
        "type": "object",
        "required": REQUIRED,
        "properties": props,
        "additionalProperties": False,
    }


def main():
    rows = json.loads(CAT.read_text(encoding="utf-8"))
    bad = 0
    for r in rows:
        errs = validate(r)
        if errs:
            bad += 1
            print(f"  ✗ {r.get('id')}: {errs[:3]}")
    SCHEMA_OUT.write_text(json.dumps(json_schema(), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"validated {len(rows)} rows · {bad} invalid · wrote {SCHEMA_OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
