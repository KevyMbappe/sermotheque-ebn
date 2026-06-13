#!/usr/bin/env python3
"""
Sermothèque EBN — series clustering (run AFTER parse_catalog.py).
Reads data/catalog.json, groups sermons into series, writes data/series.json
and enriches catalog.json in place with series_id / series_name / series_order.

Two strategies, in priority order:
  1. Thematic series  — a recurring title stem before the first ' : ' (≥3 occurrences),
                        e.g. "Fruit de l'Esprit", "Joie chrétienne", "Noël ...".
  2. Expository series — remaining sermons grouped by Bible book ("Épître aux Galates"),
                        ordered by chapter:verse.
"""
import json, re, unicodedata, collections
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CAT = ROOT / "data" / "catalog.json"

FR_BOOK = {
    "Gen": "Genèse", "Exod": "Exode", "Lev": "Lévitique", "Num": "Nombres",
    "Deut": "Deutéronome", "1Kgs": "1 Rois", "Ps": "Psaumes", "Prov": "Proverbes",
    "Isa": "Ésaïe", "Lam": "Lamentations", "Ezek": "Ézéchiel", "Matt": "Matthieu",
    "Mark": "Marc", "Luke": "Luc", "John": "Jean", "Acts": "Actes", "Rom": "Romains",
    "1Cor": "1 Corinthiens", "2Cor": "2 Corinthiens", "Gal": "Galates",
    "Eph": "Éphésiens", "Phil": "Philippiens", "Col": "Colossiens", "1Tim": "1 Timothée",
    "Heb": "Hébreux", "Jas": "Jacques", "1Pet": "1 Pierre", "1John": "1 Jean", "Rev": "Apocalypse",
}
# Correct French series name per book (epistles disambiguate recipient "aux/à" vs author "de").
SERIES_NAME = {
    "Gen": "Étude — Genèse", "Exod": "Étude — Exode", "Ps": "Étude — Psaumes",
    "Prov": "Étude — Proverbes", "Isa": "Étude — Ésaïe", "Lam": "Étude — Lamentations",
    "Ezek": "Étude — Ézéchiel",
    "Matt": "Évangile de Matthieu", "Mark": "Évangile de Marc",
    "Luke": "Évangile de Luc", "John": "Évangile de Jean", "Acts": "Actes des Apôtres",
    "Rom": "Épître aux Romains", "1Cor": "Épître aux Corinthiens",
    "2Cor": "Épître aux Corinthiens", "Gal": "Épître aux Galates",
    "Eph": "Épître aux Éphésiens", "Phil": "Épître aux Philippiens",
    "Col": "Épître aux Colossiens", "1Tim": "Épître à Timothée", "Heb": "Épître aux Hébreux",
    "Jas": "Épître de Jacques", "1Pet": "Épître de Pierre", "1John": "Épître de Jean",
    "Rev": "Apocalypse",
}


def fold(s):
    return "".join(c for c in unicodedata.normalize("NFD", (s or "").lower())
                   if unicodedata.category(c) != "Mn").strip()


def slug(s):
    s = fold(s)
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:60]


def stem_of(title):
    """recurring thematic prefix before the first ' : ' (spaced colon)"""
    if not title:
        return None
    m = re.split(r"\s+:\s+", title, maxsplit=1)
    if len(m) == 2 and len(m[0]) >= 6:
        st = re.sub(r"\s*\(.*?\)\s*$", "", m[0]).strip()   # drop trailing (…)
        # normalise the most common spelling variants (comma, accents handled by fold)
        return st
    return None


def book_series_name(osis):
    return SERIES_NAME.get(osis, f"Étude — {FR_BOOK.get(osis, osis)}")


def main():
    rows = json.loads(CAT.read_text(encoding="utf-8"))

    # --- pass 1: thematic stems ---
    stem_counts = collections.Counter(fold(stem_of(r["title"])) for r in rows if stem_of(r["title"]))
    thematic = {s for s, c in stem_counts.items() if c >= 3}
    # display name = most common original spelling for each folded stem
    disp = {}
    for r in rows:
        st = stem_of(r["title"])
        if st and fold(st) in thematic:
            disp.setdefault(fold(st), collections.Counter())[st] += 1
    stem_disp = {k: v.most_common(1)[0][0] for k, v in disp.items()}

    series = {}   # id -> {name, type, members:[idx]}

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
            rows[i]["series_id"] = None
            rows[i]["series_name"] = None

    # --- order within each series ---
    def sort_key(idx):
        r = rows[idx]
        ch = r.get("scripture_chapter") or 999
        vs = None
        if r.get("scripture_osis"):
            m = re.search(r"\.(\d+)\.(\d+)", r["scripture_osis"])
            vs = int(m.group(2)) if m else 0
        return (ch, vs or 0, r["soundcloud_id"])

    out_series = []
    for s in series.values():
        if len(s["members"]) < 2:               # a series needs ≥2 sermons
            for idx in s["members"]:
                rows[idx]["series_id"] = rows[idx]["series_name"] = None
            continue
        members = sorted(s["members"], key=sort_key)
        for order, idx in enumerate(members, 1):
            rows[idx]["series_order"] = order
        out_series.append({"id": s["id"], "name": s["name"], "type": s["type"],
                           "count": len(members)})

    out_series.sort(key=lambda s: -s["count"])
    (ROOT / "data" / "series.json").write_text(
        json.dumps(out_series, ensure_ascii=False, indent=2), encoding="utf-8")
    CAT.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    # --- report ---
    in_series = sum(1 for r in rows if r.get("series_id"))
    n = len(rows)
    print(f"Clustered {n} sermons into {len(out_series)} series "
          f"({in_series}/{n} = {100*in_series//n}% placed)")
    print("\nTop series:")
    for s in out_series[:15]:
        print(f"  [{s['type'][:4]}] {s['name']:32} {s['count']:>3}")
    print(f"\nThematic series found: {sum(1 for s in out_series if s['type']=='thematic')}")
    print(f"Expository (book) series: {sum(1 for s in out_series if s['type']=='expository')}")
    print("Wrote data/series.json and enriched data/catalog.json")


if __name__ == "__main__":
    main()
