#!/usr/bin/env python3
"""
Sermothèque EBN — first-pass catalog parser.
Reads data/raw/soundcloud_tracks.tsv (id<TAB>title) and extracts structured metadata
from the raw titles. Writes data/catalog/catalog.json + .csv and prints a coverage report.

This is the M1 "free metadata" pass; ASR/LLM enrichment fills the rest.
"""
import csv
import json
from pathlib import Path

from scripture import fold, parse_scripture, parse_speaker, parse_part, classify, clean_title, date_prefix

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "raw" / "soundcloud_tracks.tsv"
OUT = ROOT / "data" / "catalog"


def main():
    rows = []
    for line in SRC.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        line = line.replace("\\t", "\t")          # yt-dlp wrote a literal backslash-t
        sc_id, _, title = line.partition("\t")
        scr = parse_scripture(fold(title), title)
        spk = parse_speaker(title)
        rows.append({
            "soundcloud_id": sc_id,
            "raw_title": title,
            "title": clean_title(title, scr, spk),
            "language": "en" if (scr and scr["is_english"]) else "fr",
            "date": date_prefix(title),
            "speaker": spk,
            "series_part": parse_part(title),
            "scripture_osis": scr["osis"] if scr else None,
            "scripture_display": scr["display"] if scr else None,
            "scripture_book": scr["book_osis"] if scr else None,
            "scripture_chapter": scr["chapter"] if scr else None,
            "scripture_confident": scr["confident"] if scr else None,
            "kind": classify(title),
        })

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "catalog.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    with (OUT / "catalog.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    n = len(rows)
    def pct(k): return f"{k}/{n} ({100*k//n}%)"
    with_scr = sum(1 for r in rows if r["scripture_osis"])
    conf_scr = sum(1 for r in rows if r["scripture_confident"])
    books = sorted({r["scripture_book"] for r in rows if r["scripture_book"]})
    print(f"Parsed {n} SoundCloud tracks")
    print(f"  scripture parsed:      {pct(with_scr)}   (confident: {pct(conf_scr)})")
    print(f"  speaker identified:    {pct(sum(1 for r in rows if r['speaker']))}")
    print(f"  series part detected:  {pct(sum(1 for r in rows if r['series_part']))}")
    print(f"  clean title:           {pct(sum(1 for r in rows if r['title']))}")
    print(f"  English (conference):  {pct(sum(1 for r in rows if r['language'] == 'en'))}")
    print(f"  classified 'sermon':   {pct(sum(1 for r in rows if r['kind'] == 'sermon'))}")
    print(f"  distinct Bible books:  {len(books)} -> {', '.join(books)}")
    print("\nWrote data/catalog/catalog.json and .csv")


if __name__ == "__main__":
    main()
