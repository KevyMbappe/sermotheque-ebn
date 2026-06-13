#!/usr/bin/env python3
"""
Sermothèque EBN — YouTube ↔ SoundCloud matcher (run AFTER parse_catalog.py).

Key insight (2026-06-13): YouTube's Videos tab is NOT a mirror of SoundCloud. It is
heavily (a) ENGLISH-titled translations of the French sermons and (b) annual CONFERENCE
content (CBN Paris, international guests). So matching is scripture-anchored + language-aware,
not title-similarity-dominant.

Produces three buckets:
  1. same-language video match  → attach youtube_id to the SC sermon record
  2. cross-language pair        → record as a translation_of candidate on the FR sermon
  3. orphan (conference / new)  → candidate NEW catalog record (parsed), written to a file

Outputs: enriches data/catalog.json; writes data/youtube_orphans.json. Prints a report.
"""
import sys, json, re
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from parse_catalog import parse_scripture, parse_speaker, clean_title, classify, fold, BOOKS  # noqa: E402

CAT = ROOT / "data" / "catalog.json"
YT = ROOT / "data" / "youtube_videos.tsv"

TITLE_MATCH = 0.60          # same-language confident title match
TITLE_ASSIST = 0.30         # title support required alongside an exact-scripture match

EN_BOOK_WORDS = {"genesis", "psalm", "psalms", "matthew", "luke", "john", "acts",
                 "romans", "galatians", "ephesians", "philippians", "colossians",
                 "hebrews", "james", "revelation", "mark"}
EN_MARKERS = re.compile(r"\b(the|of|according|with|god's|part|sunday|professor|dr|"
                        r"praying|heart|mercy|spirit|witness|conversion|throne|"
                        r"encountered|conference)\b", re.I)
CONF_MARKERS = re.compile(r"\b(cbn\d*|good news conference|conf[ée]rence|paris 20\d\d)\b", re.I)
STOP = {"la", "le", "les", "de", "des", "du", "un", "une", "et", "en", "au", "aux", "dans",
        "par", "pour", "sur", "qui", "que", "selon", "ch", "chapitre", "partie", "part"}
BOOKWORDS = {w for b in BOOKS for w in b.split()}


def toks(title):
    ws = re.findall(r"[a-z0-9]+", fold(title))
    return {w for w in ws if len(w) > 2 and w not in STOP and w not in BOOKWORDS}


def title_sim(a, b):
    ta, tb = toks(a), toks(b)
    jac = len(ta & tb) / len(ta | tb) if (ta | tb) else 0.0
    return 0.6 * jac + 0.4 * SequenceMatcher(None, fold(a), fold(b)).ratio()


def detect(title):
    """returns (language, is_conference)"""
    f = fold(title)
    is_conf = bool(CONF_MARKERS.search(title))
    is_en = (any(w in f.split() for w in EN_BOOK_WORDS)
             or bool(EN_MARKERS.search(title)))
    return ("en" if is_en else "fr"), is_conf


def load_youtube():
    out = []
    for line in YT.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        line = line.replace("\\t", "\t")
        p = line.split("\t")
        vid, dur, title = p[0], p[1], "\t".join(p[2:])
        scr = parse_scripture(fold(title), title)
        lang, conf = detect(title)
        out.append({
            "youtube_id": vid,
            "duration": int(float(dur)) if dur not in ("NA", "") else None,
            "raw_title": title,
            "title": clean_title(title, scr, parse_speaker(title)),
            "scripture_osis": scr["osis"] if scr else None,
            "language": lang,
            "is_conference": conf,
            "speaker": parse_speaker(title),
            "kind": "qa" if "question" in fold(title) else classify(title),
        })
    return out


def main():
    sermons = json.loads(CAT.read_text(encoding="utf-8"))
    videos = load_youtube()
    by_osis = {}
    for i, s in enumerate(sermons):
        if s.get("scripture_osis"):
            by_osis.setdefault(s["scripture_osis"], []).append(i)

    same_lang = {}       # sc_idx -> (video, score)
    translations = {}    # sc_idx -> [video,...]
    orphans = []

    # rank video->best SC by title; resolve in score order so best claims win
    ranked = []
    for v in videos:
        best, bs = None, 0.0
        vt = v["title"] or v["raw_title"]                   # cleaned title (scripture stripped)
        for i, s in enumerate(sermons):
            st = s["title"] or s["raw_title"]
            sc = title_sim(vt, st)
            if v["scripture_osis"] and v["scripture_osis"] == s.get("scripture_osis"):
                sc += 0.4                                   # exact scripture range agreement
            if sc > bs:
                best, bs = i, sc
        ranked.append((v, best, bs))
    ranked.sort(key=lambda r: -r[2])

    for v, idx, sc in ranked:
        exact = idx is not None and v["scripture_osis"] and \
            v["scripture_osis"] == sermons[idx].get("scripture_osis")
        is_match = (sc >= TITLE_MATCH) or (exact and sc >= TITLE_ASSIST + 0.4)
        if is_match and idx is not None:
            if v["language"] == "fr" and idx not in same_lang:
                same_lang[idx] = (v, round(sc, 3))
                continue
            if v["language"] == "en":                       # cross-language = translation
                translations.setdefault(idx, []).append(v)
                continue
        orphans.append({**v, "best_sc_score": round(sc, 3),
                        "best_sc_title": sermons[idx]["raw_title"] if idx is not None else None})

    for i, (v, s) in same_lang.items():
        sermons[i]["youtube_id"] = v["youtube_id"]
        sermons[i]["youtube_match"] = s
    for i, vs in translations.items():
        sermons[i]["translation_candidates"] = [
            {"youtube_id": v["youtube_id"], "title": v["raw_title"], "language": v["language"]}
            for v in vs]

    (ROOT / "data" / "youtube_orphans.json").write_text(
        json.dumps(orphans, ensure_ascii=False, indent=2), encoding="utf-8")
    CAT.write_text(json.dumps(sermons, ensure_ascii=False, indent=2), encoding="utf-8")

    n = len(sermons)
    conf_orph = sum(1 for o in orphans if o["is_conference"])
    en_orph = sum(1 for o in orphans if o["language"] == "en")
    print(f"SoundCloud sermons: {n} | YouTube videos: {len(videos)}")
    print(f"  ① same-language video attached:   {len(same_lang)}/{n} SC sermons")
    print(f"  ② cross-language (translation) :   {sum(len(v) for v in translations.values())} videos "
          f"→ {len(translations)} FR sermons")
    print(f"  ③ orphans (candidate new records): {len(orphans)}")
    print(f"        ├─ conference content: {conf_orph}")
    print(f"        └─ English-language:   {en_orph}")
    print(f"\nWrote data/youtube_orphans.json; enriched data/catalog.json")
    if translations:
        print("\nSample translation pairs (EN video ↔ FR sermon):")
        for i, vs in list(translations.items())[:5]:
            print(f"  FR {sermons[i]['raw_title'][:46]!r}")
            print(f"  EN {vs[0]['raw_title'][:46]!r}")


if __name__ == "__main__":
    main()
