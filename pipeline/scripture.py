#!/usr/bin/env python3
"""
Sermothèque EBN — shared parsing primitives.
Used by parse_catalog.py and match_youtube.py. No I/O here; pure functions.

Covers: accent folding, OSIS Bible-book mapping (FR + EN), scripture-reference parsing,
speaker extraction, series-part detection, content classification, title cleaning.
"""
import re
import unicodedata

# ---- OSIS book map (French + English + common abbreviations) ----
BOOKS = {
    "genese": "Gen", "exode": "Exod", "levitique": "Lev", "nombres": "Num",
    "deuteronome": "Deut", "josue": "Josh", "juges": "Judg", "ruth": "Ruth",
    "1 samuel": "1Sam", "2 samuel": "2Sam", "1 rois": "1Kgs", "2 rois": "2Kgs",
    "1 chroniques": "1Chr", "2 chroniques": "2Chr", "esdras": "Ezra",
    "nehemie": "Neh", "esther": "Esth", "job": "Job", "psaume": "Ps", "psaumes": "Ps",
    "proverbes": "Prov", "ecclesiaste": "Eccl", "cantique": "Song",
    "cantique des cantiques": "Song", "esaie": "Isa", "isaie": "Isa", "jeremie": "Jer",
    "lamentations": "Lam", "ezechiel": "Ezek", "daniel": "Dan", "osee": "Hos",
    "joel": "Joel", "amos": "Amos", "abdias": "Obad", "jonas": "Jonah", "michee": "Mic",
    "nahum": "Nah", "habacuc": "Hab", "sophonie": "Zeph", "aggee": "Hag",
    "zacharie": "Zech", "malachie": "Mal", "matthieu": "Matt", "marc": "Mark",
    "luc": "Luke", "jean": "John", "actes": "Acts", "romains": "Rom",
    "1 corinthiens": "1Cor", "2 corinthiens": "2Cor", "galates": "Gal",
    "ephesiens": "Eph", "philippiens": "Phil", "colossiens": "Col",
    "1 thessaloniciens": "1Thess", "2 thessaloniciens": "2Thess",
    "1 timothee": "1Tim", "2 timothee": "2Tim", "1 tim": "1Tim", "2 tim": "2Tim",
    "tite": "Titus", "philemon": "Phlm", "hebreux": "Heb", "jacques": "Jas",
    "1 pierre": "1Pet", "2 pierre": "2Pet", "1 jean": "1John", "2 jean": "2John",
    "3 jean": "3John", "jude": "Jude", "apocalypse": "Rev",
    # English
    "genesis": "Gen", "psalm": "Ps", "psalms": "Ps", "matthew": "Matt", "mark": "Mark",
    "luke": "Luke", "john": "John", "acts": "Acts", "romans": "Rom", "galatians": "Gal",
    "ephesians": "Eph", "philippians": "Phil", "colossians": "Col", "hebrews": "Heb",
    "james": "Jas", "revelation": "Rev",
}
EN_BOOKS = {"genesis", "psalm", "psalms", "matthew", "luke", "john", "acts", "romans",
            "galatians", "ephesians", "philippians", "colossians", "hebrews", "james",
            "revelation", "mark"}

SPEAKERS = ["David Pelosi", "Stephan Kongo", "Loïc Rakotozafy", "Nathanaël Fis",
            "Christian Bouedjoro", "Joël Beeke", "Jonas Hensworth"]

ROMAN = {"i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6, "vii": 7, "viii": 8,
         "ix": 9, "x": 10}

NON_SERMON = ("questions et reponses", "questions - reponses", "evaluation",
              "formation", "lecon", "introduction au panorama")


def fold(s):
    """lowercase + strip accents for matching"""
    return "".join(c for c in unicodedata.normalize("NFD", (s or "").lower())
                   if unicodedata.category(c) != "Mn")


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
    norm = ref.replace("à", "-").replace("–", "-").replace("—", "-")
    norm = re.sub(r"ch(?:apitre|\.)?", " ", norm)
    norm = re.sub(r"\bv\b", " ", norm)
    nums = [int(n) for n in re.findall(r"\d+", norm)]
    chapter = verse_start = verse_end = end_chapter = None
    confident = True
    cross_chapter = ref.count(":") >= 2 and len(nums) >= 4
    if not nums:
        confident = False
    elif cross_chapter:
        chapter, verse_start, end_chapter, verse_end = nums[0], nums[1], nums[2], nums[3]
    elif len(nums) == 1:
        chapter = nums[0]
    elif len(nums) == 2:
        chapter, verse_start = nums[0], nums[1]
        verse_end = verse_start
    else:
        chapter, verse_start = nums[0], nums[1]
        verse_end = nums[-1]
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
        "book_osis": osis_book, "chapter": chapter, "verse_start": verse_start,
        "verse_end": verse_end, "osis": osis,
        "display": re.sub(r"\s+", " ", original[m.start():].strip()),
        "is_english": book_key in EN_BOOKS, "confident": confident,
    }


def parse_speaker(title):
    for name in SPEAKERS:
        if fold(name) in fold(title):
            return name
    m = re.search(r"(?:Pr\.?|Pasteur)\s+([A-ZÀ-Ÿ][\wÀ-ÿ’'.-]+(?:\s+[A-ZÀ-Ÿ][\wÀ-ÿ’'.-]+)+)", title)
    if m:
        return m.group(1).strip()
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
        return ROMAN.get(v) or (int(v) if v.isdigit() else None)
    m = re.search(r"le[çc]on\s*n?°?\s*(\d+)", f)
    if m:
        return int(m.group(1))
    m = re.search(r"\(\s*([ivx]+|\d+)\s*\)\s*$", f)
    if m:
        v = m.group(1)
        return ROMAN.get(v) or (int(v) if v.isdigit() else None)
    return None


def classify(title):
    f = fold(title)
    if f.strip() in ("introduction",) or f.startswith("lecon"):
        return "teaching"
    if any(k in f for k in NON_SERMON):
        return "teaching_or_qa"
    return "sermon"


def clean_title(original, scripture, speaker):
    t = original
    t = re.sub(r"^\s*20\d\d[_/]\d\d[_/]\d\d\s*\|?\s*", "", t)
    if scripture and scripture["display"] in original:
        t = t[:original.find(scripture["display"])]
    if speaker:
        t = re.sub(re.escape(speaker), "", t)
    t = re.sub(r"\(\s*(?:pr\.?\s*)?[^)]*\)", "", t, flags=re.I)
    t = t.strip(" |-–—:•\t")
    t = re.sub(r"\s+", " ", t)
    return t or None


def date_prefix(original):
    m = re.match(r"\s*(20\d\d)[_/](\d\d)[_/](\d\d)", original)
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else None
