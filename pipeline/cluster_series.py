#!/usr/bin/env python3
"""
Sermothèque EBN — series clustering (run AFTER parse_catalog.py).
Reads data/catalog/catalog.json, groups sermons into series, writes data/catalog/series.json
and enriches catalog.json with series_id / series_name / series_order.

Strategies (priority order):
  1. Thematic series  — recurring title stem before the first ' : ' (≥3 occurrences).
  2. Expository series — remaining sermons grouped by Bible book, ordered by chapter:verse.
"""
import collections
import json
import re
from pathlib import Path

from scripture import fold

ROOT = Path(__file__).resolve().parent.parent
CAT = ROOT / "data" / "catalog" / "catalog.json"

FR_BOOK = {
    "Gen": "Genèse", "Ps": "Psaumes", "Prov": "Proverbes", "Isa": "Ésaïe",
    "Lam": "Lamentations", "Ezek": "Ézéchiel", "Matt": "Matthieu", "Mark": "Marc",
    "Luke": "Luc", "John": "Jean", "Acts": "Actes", "Rom": "Romains", "Gal": "Galates",
    "Eph": "Éphésiens", "Phil": "Philippiens", "Col": "Colossiens", "1Tim": "1 Timothée",
    "Heb": "Hébreux", "Jas": "Jacques", "1Pet": "1 Pierre", "1John": "1 Jean", "Rev": "Apocalypse",
}
# Correct French series name per book (recipients "aux/à" vs author "de").
SERIES_NAME = {
    "Gen": "Étude — Genèse", "Ps": "Étude — Psaumes", "Prov": "Étude — Proverbes",
    "Isa": "Étude — Ésaïe", "Lam": "Étude — Lamentations", "Ezek": "Étude — Ézéchiel",
    "Matt": "Évangile de Matthieu", "Mark": "Évangile de Marc", "Luke": "Évangile de Luc",
    "John": "Évangile de Jean", "Acts": "Actes des Apôtres", "Rom": "Épître aux Romains",
    "1Cor": "Épître aux Corinthiens", "2Cor": "Épître aux Corinthiens",
    "Gal": "Épître aux Galates", "Eph": "Épître aux Éphésiens", "Phil": "Épître aux Philippiens",
    "Col": "Épître aux Colossiens", "1Tim": "Épître à Timothée", "Heb": "Épître aux Hébreux",
    "Jas": "Épître de Jacques", "1Pet": "Épître de Pierre", "1John": "Épître de Jean",
    "Rev": "Apocalypse",
}


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", fold(s)).strip("-")[:60]


def stem_of(title):
    if not title:
        return None
    m = re.split(r"\s+:\s+", title, maxsplit=1)
    if len(m) == 2 and len(m[0]) >= 6:
        return re.sub(r"\s*\(.*?\)\s*$", "", m[0]).strip()
    return None


def book_series_name(osis):
    return SERIES_NAME.get(osis, f"Étude — {FR_BOOK.get(osis, osis)}")


def write_csv(rows):
    """flattened, spreadsheet-friendly export of the unified catalog"""
    import csv
    # The CSV is a flat data export (not UI) — carry provenance + enrichment so a single
    # expensive run never loses information. List fields are joined with " | ".
    scalar = ["id", "source", "title", "language", "date", "audio_duration", "video_duration",
              "speaker", "speaker_provenance", "series_name", "series_part", "series_order",
              "scripture_osis", "scripture_book", "primary_scripture", "kind", "is_conference",
              "description", "invitation", "summary", "transcript_ref"]
    joined = ["topics", "key_points", "references", "scripture_refs", "scripture_refs_osis",
              "questions"]
    # key_quotes / chapters carry timestamps (nested objects) — JSON only, not flattened to CSV.
    cols = scalar + ["soundcloud_id", "youtube_id"] + joined
    with (CAT.parent / "catalog.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            media = r.get("media") or {}
            row = {k: r.get(k) for k in scalar}
            row["soundcloud_id"] = media.get("soundcloud_id")
            row["youtube_id"] = media.get("youtube_id")
            for k in joined:
                row[k] = " | ".join(r.get(k) or [])
            w.writerow(row)


def main():
    rows = json.loads(CAT.read_text(encoding="utf-8"))

    stem_counts = collections.Counter(fold(stem_of(r["title"])) for r in rows if stem_of(r["title"]))
    thematic = {s for s, c in stem_counts.items() if c >= 3}
    disp = {}
    for r in rows:
        st = stem_of(r["title"])
        if st and fold(st) in thematic:
            disp.setdefault(fold(st), collections.Counter())[st] += 1
    stem_disp = {k: v.most_common(1)[0][0] for k, v in disp.items()}

    series = {}

    def ensure(sid, name, stype):
        series.setdefault(sid, {"id": sid, "name": name, "type": stype, "members": []})
        return sid

    for i, r in enumerate(rows):
        st = stem_of(r["title"])
        assigned = None
        if st and fold(st) in thematic:
            name = stem_disp[fold(st)]
            assigned = ensure("ser-" + slug(name), name, "thematic")
        elif r.get("scripture_book"):
            name = book_series_name(r["scripture_book"])
            assigned = ensure("ser-" + slug(name), name, "expository")
        if assigned:
            series[assigned]["members"].append(i)
            rows[i]["series_id"] = assigned
            rows[i]["series_name"] = series[assigned]["name"]
        else:
            rows[i]["series_id"] = rows[i]["series_name"] = None

    def sort_key(idx):
        r = rows[idx]
        ch = r.get("scripture_chapter") or 999
        m = re.search(r"\.(\d+)\.(\d+)", r.get("scripture_osis") or "")
        return (ch, int(m.group(2)) if m else 0, r["id"])

    out_series = []
    for s in series.values():
        if len(s["members"]) < 2:
            for idx in s["members"]:
                rows[idx]["series_id"] = rows[idx]["series_name"] = None
            continue
        for order, idx in enumerate(sorted(s["members"], key=sort_key), 1):
            rows[idx]["series_order"] = order
        out_series.append({"id": s["id"], "name": s["name"], "type": s["type"],
                          "count": len(s["members"])})

    out_series.sort(key=lambda s: -s["count"])
    (CAT.parent / "series.json").write_text(
        json.dumps(out_series, ensure_ascii=False, indent=2), encoding="utf-8")
    CAT.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    write_csv(rows)

    in_series = sum(1 for r in rows if r.get("series_id"))
    n = len(rows)
    print(f"Clustered {n} sermons into {len(out_series)} series "
          f"({in_series}/{n} = {100*in_series//n}% placed)")
    print("\nTop series:")
    for s in out_series[:15]:
        print(f"  [{s['type'][:4]}] {s['name']:32} {s['count']:>3}")
    print("\nWrote data/catalog/series.json and enriched data/catalog/catalog.json")


if __name__ == "__main__":
    main()
