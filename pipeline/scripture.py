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


# ---- citation-style reference normalisation (decision #56) ----
# `parse_scripture` above is TITLE-oriented: one reference, embedded in noise, and it is
# deliberately left untouched (the structural catalog depends on its exact behaviour).
# The LLM-produced `scripture_refs` are a different animal: short, already-isolated citation
# strings, but many per sermon and in every French shape a preacher uses — chapter ranges
# ("Genèse 9-10"), verse lists ("Jean 1:1,14"), dot separators ("Josué 1.8"), cross-chapter
# spans, book-only allusions, and parenthetical glosses ("Luc 15 (fils prodigue)").
# These functions turn one such string into zero or more OSIS ids, reusing the BOOKS table.
# Rule of the house: never guess. Unrecognised book → [] (the caller counts the misses).

# A book name only counts as a whole token — never inside a hyphenated name, so
# "Jean-Baptiste" / "Saint-Jean" are not read as the gospel of John.
_BOOK_TOKEN_RE = re.compile(
    r"(?<![-\w])(?P<book>" + "|".join(re.escape(b) for b in _BOOK_ALT) + r")(?![-\w])"
)
# the numeric tail of a citation: digits plus the separators French refs actually use
_REF_EXPR_RE = re.compile(r"^[\s:]*(\d[\d\s:.,;\-]*)")
_PARENS_RE = re.compile(r"\(([^)]*)\)|\[([^\]]*)\]")


def _normalize_ref_text(s):
    """Fold to the matching alphabet, then reduce French ref vocabulary to punctuation.
    The preposition meaning 'to' is handled AFTER folding (as a bare `a`) on purpose: a literal
    accented character in a pattern is a normalisation trap (NFC vs NFD) -- see decision #56."""
    s = (s or "").replace("–", "-").replace("—", "-").replace("−", "-")
    f = fold(s)
    f = re.sub(r"(?<=[\s\d])a(?=[\s\d])", "-", f)   # a bare "a" between numbers = "to"
    f = re.sub(r"\bch(?:apitres?|ap)?\.?(?=\s*\d)", " ", f)    # "ch. 2", "chapitre 2" → dropped
    f = re.sub(r"(?<=\d)\s*\b(?:versets?|vv?)\.?\s*(?=\d)", ":", f)   # "2 v 11" → "2:11"
    f = re.sub(r"\b(?:versets?|vv?)\.?(?=\s*\d)", " ", f)      # leading "verset 5" → dropped
    f = re.sub(r"(?<=\d)\s*\bet\b\s*(?=\d)", ",", f)           # "1:1 et 14" → a verse list
    return f


def _point(tok):
    """'12:5' → (12, 5) explicit chapter:verse · '12' → (None, 12) bare number."""
    if ":" in tok:
        a, b = tok.split(":", 1)
        return int(a), int(b)
    return None, int(tok)


def _resolve(pt, ctx, verse_mode):
    """Bare numbers are ambiguous: a verse when a chapter:verse context is open
    ('Jean 1:1,14'), another chapter otherwise ('Genèse 9-10').
    Returns (chapter, verse|None, new_ctx, new_verse_mode)."""
    c, n = pt
    if c is not None:
        return c, n, c, True
    if verse_mode and ctx is not None:
        return ctx, n, ctx, True
    return n, None, n, False


# Books with a single chapter: a bare number there is a VERSE, never a chapter
# ('Jude 24-25' = verses 24-25 → Jude.1.24-Jude.1.25). OSIS still numbers the chapter 1.
ONE_CHAPTER_BOOKS = {"Obad", "Phlm", "2John", "3John", "Jude"}


def _parse_expr(expr, one_chapter=False):
    """Numeric tail of a citation → list of (chapter, verse, end_chapter, end_verse) spans."""
    expr = re.sub(r"(?<=\d)\s*\.\s*(?=\d)", ":", expr)   # 'Josué 1.8' — dot separates c.v
    expr = expr.replace(";", ",").replace(".", ",")      # stray dot/semicolon = segment break
    spans, ctx, verse_mode = [], (1 if one_chapter else None), one_chapter
    for part in expr.split(","):
        ends = [p.strip() for p in part.split("-") if p.strip()]
        if not ends or not all(re.fullmatch(r"\d+(?::\d+)?", e) for e in ends):
            continue                                     # unparseable segment → skipped, not guessed
        c1, v1, ctx, verse_mode = _resolve(_point(ends[0]), ctx, verse_mode)
        if len(ends) > 1:
            c2, v2, _, _ = _resolve(_point(ends[-1]), ctx, verse_mode)
        else:
            c2, v2 = c1, v1
        spans.append((c1, v1, c2, v2))
    return spans


def _osis(book, span):
    c1, v1, c2, v2 = span
    start = f"{book}.{c1}" + (f".{v1}" if v1 else "")
    if (c2, v2) == (c1, v1):
        return start
    return f"{start}-{book}.{c2}" + (f".{v2}" if v2 else "")


def _parse_chunk(text):
    """One chunk may name several books ('Romains 8 et Éphésiens 2'): each book owns the
    numbers that follow it, up to the next book name."""
    f = _normalize_ref_text(text)
    matches = list(_BOOK_TOKEN_RE.finditer(f))
    out = []
    for i, m in enumerate(matches):
        tail_end = matches[i + 1].start() if i + 1 < len(matches) else len(f)
        book = BOOKS[m.group("book")]
        em = _REF_EXPR_RE.match(f[m.end():tail_end])
        spans = _parse_expr(em.group(1), book in ONE_CHAPTER_BOOKS) if em else []
        out += [_osis(book, s) for s in spans] or [book]     # no numbers → book-level id
    return out


def _is_reference_like(text):
    """A parenthetical is only re-parsed when it *is* a citation ('(1 Jean 5:1)'), never when
    it is a gloss ('(fils prodigue)', '(allusion)')."""
    f = _normalize_ref_text(text).strip()
    m = _BOOK_TOKEN_RE.match(f)
    return bool(m and _REF_EXPR_RE.match(f[m.end():]))


def parse_reference(text):
    """Free-text scripture citation (FR/EN) → ordered, de-duplicated list of OSIS ids.
    Returns [] when no Bible book can be recognised — misses are counted, never guessed."""
    if not isinstance(text, str) or not text.strip():
        return []
    glosses = [g or h for g, h in _PARENS_RE.findall(text)]
    chunks = [_PARENS_RE.sub(" ", text)] + [g for g in glosses if _is_reference_like(g)]
    ids, seen = [], set()
    for osis_id in (i for c in chunks for i in _parse_chunk(c)):
        if osis_id not in seen:
            seen.add(osis_id)
            ids.append(osis_id)
    return ids


def normalize_refs(refs):
    """A sermon's free-text `scripture_refs` → `scripture_refs_osis`: OSIS ids, de-duplicated,
    in order of first appearance. References that don't parse are dropped (see #56)."""
    ids, seen = [], set()
    for raw in refs or []:
        for osis_id in parse_reference(raw):
            if osis_id not in seen:
                seen.add(osis_id)
                ids.append(osis_id)
    return ids


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


# The regular preacher (lusophone-accented) — untagged sermons are his. Decision #45.
DEFAULT_SPEAKER = "David Pelosi"


def resolve_speaker(title, *, is_conference=False, is_english=False):
    """Explicit speaker named in the title, else the regular preacher — except for
    conference or English sermons, which are typically named guests, so we leave those
    unattributed rather than mis-credit them to the pastor."""
    spk = parse_speaker(title)
    if spk:
        return spk
    return None if (is_conference or is_english) else DEFAULT_SPEAKER


def speaker_provenance(title, *, is_conference=False, is_english=False):
    """How `speaker` was decided — so the human sweep / fingerprint gate can find guesses.
    'title' (named explicitly) | 'default-rule' (assumed David, #45) | None (left blank)."""
    if parse_speaker(title):
        return "title"
    return None if (is_conference or is_english) else "default-rule"


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
