#!/usr/bin/env python3
"""
Sermothèque EBN — fold YouTube orphans into the unified catalog (run AFTER match_youtube.py,
BEFORE cluster_series.py).

Turns the SoundCloud-only catalog (239) + the YouTube orphans (228 net-new videos) into one
uniform record set (~467) with a `source` field, a `media` object, and placeholders for the
enrichment fields (topics/summary/transcript). Pipeline order: parse → match → fold → cluster.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CAT = ROOT / "data" / "catalog" / "catalog.json"
ORPH = ROOT / "data" / "catalog" / "youtube_orphans.json"


def osis_book_chapter(osis):
    if not osis:
        return None, None
    m = re.match(r"([^.]+)\.(\d+)", osis)
    return (m.group(1), int(m.group(2))) if m else (osis, None)


# canonical key order for every unified record
CANON = ["id", "source", "raw_title", "title", "language", "date",
         "audio_duration", "video_duration", "speaker",
         "series_id", "series_name", "series_part", "series_order",
         "scripture_osis", "scripture_display", "scripture_book", "scripture_chapter",
         "scripture_confident", "kind", "is_conference", "media",
         "youtube_match", "translation_candidates", "topics", "summary", "transcript_ref"]


def canonical(d):
    """project a partial dict onto the canonical schema (missing → None / [])"""
    out = {k: d.get(k) for k in CANON}
    out["topics"] = d.get("topics") or []
    out["translation_candidates"] = d.get("translation_candidates") or []
    out["is_conference"] = bool(d.get("is_conference"))
    return out


def main():
    sc = json.loads(CAT.read_text(encoding="utf-8"))
    orphans = json.loads(ORPH.read_text(encoding="utf-8"))

    unified = []
    # 1) SoundCloud records
    for r in sc:
        r["id"] = "sc-" + r["soundcloud_id"]
        r["source"] = "soundcloud"
        r["media"] = {"soundcloud_id": r["soundcloud_id"], "youtube_id": r.get("youtube_id")}
        unified.append(canonical(r))
    # 2) YouTube orphans → records with the same shape
    for o in orphans:
        book, chap = osis_book_chapter(o.get("scripture_osis"))
        unified.append(canonical({
            "id": "yt-" + o["youtube_id"], "source": "youtube",
            "raw_title": o["raw_title"], "title": o.get("title"),
            "language": o.get("language", "fr"),
            "video_duration": o.get("duration"), "speaker": o.get("speaker"),
            "scripture_osis": o.get("scripture_osis"), "scripture_book": book, "scripture_chapter": chap,
            "kind": o.get("kind", "sermon"), "is_conference": o.get("is_conference"),
            "media": {"soundcloud_id": None, "youtube_id": o["youtube_id"]},
        }))
    CAT.write_text(json.dumps(unified, ensure_ascii=False, indent=2), encoding="utf-8")

    # report
    import collections
    by_src = collections.Counter(r["source"] for r in unified)
    conf = sum(1 for r in unified if r.get("is_conference"))
    en = sum(1 for r in unified if r.get("language") == "en")
    print(f"Unified catalog: {len(unified)} records "
          f"(soundcloud {by_src['soundcloud']} + youtube {by_src['youtube']})")
    print(f"  conference: {conf} | English: {en}")
    print("Wrote data/catalog/catalog.json (run cluster_series.py next)")


if __name__ == "__main__":
    main()
