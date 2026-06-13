#!/usr/bin/env python3
"""
Sermothèque EBN — first-pass catalog parser.
Reads data/soundcloud_tracks.tsv (id<TAB>title) and extracts structured metadata
(title, OSIS scripture, speaker, series part, language, kind) from the raw titles.
Outputs data/catalog.json + data/catalog.csv and prints a coverage report.

Pure stdlib. This is the M1 "free metadata" pass; ASR/LLM enrichment fills the rest.
"""
import csv, json, re, sys, unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "soundcloud_tracks.tsv"

# ---- OSIS book map (French + English + common abbreviations) ----
# name (lowercased, accent-folded) -> OSIS id
BOOKS = {
    # Pentateuch
    "genese": "Gen", "exode": "Exod", "levitique": "Lev", "nombres": "Num",
    "deuteronome": "Deut",
    # History
    "josue": "Josh", "juges": "Judg", "ruth": "Ruth",
    "1 samuel": "1Sam", "2 samuel": "2Sam", "1 rois": "1Kgs", "2 rois": "2Kgs",
    "1 chroniques": "1Chr", "2 chroniques": "2Chr", "esdras": "Ezra",
    "nehemie": "Neh", "esther": "Esth",
    # Wisdom
    "job": "Job", "psaume": "Ps", "psaumes": "Ps", "proverbes": "Prov",
    "ecclesiaste": "Eccl", "cantique": "Song", "cantique des cantiques": "Song",
    # Major prophets
    "esaie": "Isa", "isaie": "Isa", "jeremie": "Jer", "lamentations": "Lam",
    "ezechiel": "Ezek", "daniel": "Dan",
    # Minor prophets
    "osee": "Hos", "joel": "Joel", "amos": "Amos", "abdias": "Obad",
    "jonas": "Jonah", "michee": "Mic", "nahum": "Nah", "habacuc": "Hab",
    "sophonie": "Zeph", "aggee": "Hag", "zacharie": "Zech", "malachie": "Mal",
    # Gospels + Acts
    "matthieu": "Matt", "marc": "Mark", "luc": "Luke", "jean": "John",
    "actes": "Acts",
    # Pauline
    "romains": "Rom", "1 corinthiens": "1Cor", "2 corinthiens": "2Cor",
    "galates": "Gal", "ephesiens": "Eph", "philippiens": "Phil",
    "colossiens": "Col", "1 thessaloniciens": "1Thess", "2 thessaloniciens": "2Thess",
    "1 timothee": "1Tim", "2 timothee": "2Tim", "1 tim": "1Tim", "2 tim": "2Tim",
    "tite": "Titus", "philemon": "Phlm",
    # General
    "hebreux": "Heb", "jacques": "Jas", "1 pierre": "1Pet", "2 pierre": "2Pet",
    "1 jean": "1John", "2 jean": "2John", "3 jean": "3John", "jude": "Jude",
    "apocalypse": "Rev",
    # A few English names (conference content)
    "genesis": "Gen", "psalm": "Ps", "psalms": "Ps", "matthew": "Matt",
    "mark": "Mark", "luke": "Luke", "john": "John", "acts": "Acts",
    "romans": "Rom", "galatians": "Gal", "ephesians": "Eph",
    "philippians": "Phil", "colossians": "Col", "hebrews": "Heb",
    "james": "Jas", "revelation": "Rev",
}
EN_BOOKS = {"genesis", "psalm", "psalms", "matthew", "luke", "john", "acts",
            "romans", "galatians", "ephesians", "philippians", "colossians",
            "hebrews", "james", "revelation", "mark"}

# Known speakers (built from the clear cases in the data); matched anywhere.
SPEAKERS = [
    "David Pelosi", "Stephan Kongo", "Loïc Rakotozafy", "Nathanaël Fis",
    "Christian Bouedjoro", "Joël Beeke", "Jonas Hensworth",
]

ROMAN = {"i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6, "vii": 7,
         "viii": 8, "ix": 9, "x": 10}


def fold(s: str) -> str:
    """lowercase + strip accents for matching"""
    return "".join(c for c in unicodedata.normalize("NFD", s.lower())
                   if unicodedata.category(c) != "Mn")


# book-name alternation, longest first so "1 jean" beats "jean"
_BOOK_ALT = sorted(BOOKS.keys(), key=len, reverse=True)
_BOOK_RE = re.compile(
    r"(?P<book>" + "|".join(re.escape(b) for b in _BOOK_ALT) + r")"
    r"\s*(?P<ref>(?:ch(?:apitre|\.)?\s*)?\d[\d\s:.,và\-–—]*)?",
)


def parse_scripture(folded_title, original):
    m = _BOOK_RE.search(folded_title)
    if not m:
        return None
    book_key = m.group("book")
    osis_book = BOOKS[book_key]
    ref = (m.group("ref") or "").strip()
    # normalise the reference string
    norm = ref.replace("à", "-").replace("–", "-").replace("—", "-")
    norm = re.sub(r"ch(?:apitre|\.)?", " ", norm)
    norm = re.sub(r"\bv\b", " ", norm)
    nums = [int(n) for n in re.findall(r"\d+", norm)]
    chapter = verse_start = verse_end = end_chapter = None
    confident = True
    cross_chapter = ref.count(":") >= 2 and len(nums) >= 4
    if not nums:
        confident = False
    elif cross_chapter:                          # "1 : 26 - 2 : 3"
        chapter, verse_start, end_chapter, verse_end = nums[0], nums[1], nums[2], nums[3]
    elif len(nums) == 1:
        chapter = nums[0]                        # chapter only
    elif len(nums) == 2:
        chapter, verse_start = nums[0], nums[1]
        verse_end = verse_start
    else:
        chapter, verse_start = nums[0], nums[1]
        verse_end = nums[-1]                      # span (handles multi-range loosely)
    # OSIS
    if chapter and verse_start:
        osis = f"{osis_book}.{chapter}.{verse_start}"
        ec = end_chapter or chapter
        if (ec, verse_end) != (chapter, verse_start) and verse_end:
            osis += f"-{osis_book}.{ec}.{verse_end}"
    elif chapter:
        osis = f"{osis_book}.{chapter}"
    else:
        osis = osis_book
    return {
        "book_osis": osis_book,
        "chapter": chapter,
        "verse_start": verse_start,
        "verse_end": verse_end,
        "osis": osis,
        "display": re.sub(r"\s+", " ", original[m.start():].strip()),
        "is_english": book_key in EN_BOOKS,
        "confident": confident,
    }


def parse_speaker(title):
    for name in SPEAKERS:
        if fold(name) in fold(title):
            return name
    m = re.search(r"(?:Pr\.?|Pasteur)\s+([A-ZÀ-Ÿ][\wÀ-ÿ’'.-]+(?:\s+[A-ZÀ-Ÿ][\wÀ-ÿ’'.-]+)+)", title)
    if m:
        return m.group(1).strip()
    # parenthetical proper name that is NOT a series marker
    for pm in re.findall(r"\(([^)]+)\)", title):
        pf = fold(pm)
        if any(w in pf for w in ("chapitre", "partie", "part ")):
            continue
        if re.fullmatch(r"[ivx]+", pf.strip()) or pf.strip().isdigit():
            continue
        if re.fullmatch(r"[A-ZÀ-Ÿ][\wÀ-ÿ’'.-]+(?:\s+[A-ZÀ-Ÿ][\wÀ-ÿ’'.-]+)+", pm.strip()):
            return re.sub(r"^Pr\.?\s*", "", pm.strip())
    return None


def parse_part(title):
    f = fold(title)
    m = re.search(r"partie\s+([ivx]+|\d+)", f)
    if m:
        v = m.group(1)
        return ROMAN.get(v, None) or (int(v) if v.isdigit() else None)
    m = re.search(r"le[çc]on\s*n?°?\s*(\d+)", f)
    if m:
        return int(m.group(1))
    m = re.search(r"\(\s*([ivx]+|\d+)\s*\)\s*$", f)   # trailing (II) / ( 2 )
    if m:
        v = m.group(1)
        return ROMAN.get(v, None) or (int(v) if v.isdigit() else None)
    return None


NON_SERMON = ("questions et reponses", "questions - reponses", "evaluation",
              "formation", "lecon", "introduction au panorama")


def classify(title):
    f = fold(title)
    if f.strip() in ("introduction",) or f.startswith("lecon"):
        return "teaching"
    if any(k in f for k in NON_SERMON):
        return "teaching_or_qa"
    return "sermon"


def clean_title(original, scripture, speaker):
    t = original
    # strip leading date prefix
    t = re.sub(r"^\s*20\d\d[_/]\d\d[_/]\d\d\s*\|?\s*", "", t)
    if scripture:
        t = t[:original.find(scripture["display"])] if scripture["display"] in original else t
    if speaker:
        t = re.sub(re.escape(speaker), "", t)
    t = re.sub(r"\(\s*(?:pr\.?\s*)?[^)]*\)", "", t, flags=re.I)  # leftover parens
    t = t.strip(" |-–—:•\t")
    t = re.sub(r"\s+", " ", t)
    return t or None


def date_prefix(original):
    m = re.match(r"\s*(20\d\d)[_/](\d\d)[_/](\d\d)", original)
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else None


def main():
    rows = []
    for line in SRC.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        line = line.replace("\\t", "\t")          # yt-dlp wrote a literal backslash-t
        sc_id, _, title = line.partition("\t")
        f = fold(title)
        scr = parse_scripture(f, title)
        spk = parse_speaker(title)
        part = parse_part(title)
        rec = {
            "soundcloud_id": sc_id,
            "raw_title": title,
            "title": clean_title(title, scr, spk),
            "language": "en" if (scr and scr["is_english"]) else "fr",
            "date": date_prefix(title),
            "speaker": spk,
            "series_part": part,
            "scripture_osis": scr["osis"] if scr else None,
            "scripture_display": scr["display"] if scr else None,
            "scripture_book": scr["book_osis"] if scr else None,
            "scripture_chapter": scr["chapter"] if scr else None,
            "scripture_confident": scr["confident"] if scr else None,
            "kind": classify(title),
        }
        rows.append(rec)

    (ROOT / "data" / "catalog.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    with (ROOT / "data" / "catalog.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)

    # ---- coverage report ----
    n = len(rows)
    def pct(k): return f"{k}/{n} ({100*k//n}%)"
    with_scr = sum(1 for r in rows if r["scripture_osis"])
    conf_scr = sum(1 for r in rows if r["scripture_confident"])
    with_spk = sum(1 for r in rows if r["speaker"])
    with_part = sum(1 for r in rows if r["series_part"])
    with_title = sum(1 for r in rows if r["title"])
    en = sum(1 for r in rows if r["language"] == "en")
    sermons = sum(1 for r in rows if r["kind"] == "sermon")
    books = sorted({r["scripture_book"] for r in rows if r["scripture_book"]})
    print(f"Parsed {n} SoundCloud tracks")
    print(f"  scripture parsed:      {pct(with_scr)}   (confident: {pct(conf_scr)})")
    print(f"  speaker identified:    {pct(with_spk)}")
    print(f"  series part detected:  {pct(with_part)}")
    print(f"  clean title:           {pct(with_title)}")
    print(f"  English (conference):  {pct(en)}")
    print(f"  classified 'sermon':   {pct(sermons)}")
    print(f"  distinct Bible books:  {len(books)} -> {', '.join(books)}")
    print(f"\nWrote data/catalog.json and data/catalog.csv")


if __name__ == "__main__":
    main()
