#!/usr/bin/env python3
"""
Sermothèque EBN — the single entry point: a set of YT/SC ids/URLs in, one canonical
catalog entry out.

    build_entry(source, *, transcribe, enrich) -> entry dict

`source` is a dict with at least one of: soundcloud_id, youtube_id, soundcloud_url,
youtube_url; plus optional `raw_title` and `audio_path`. The two external steps —
`transcribe` and `enrich` — are injected, so this composes cleanly and is testable
end-to-end with fakes (no network, no cost). Production wires the real adapters from
transcribe.py / enrich.py; tests pass stubs.

Pipeline:  parse title → transcribe → enrich → assemble (+ persist transcript to git).
"""
import json
import os
from pathlib import Path

from scripture import fold, parse_scripture, parse_speaker, parse_part, classify, clean_title, date_prefix

ROOT = Path(__file__).resolve().parent.parent
TRANSCRIPTS = ROOT / "data" / "catalog" / "transcripts"


def load_dotenv(path=ROOT / ".env"):
    """Minimal KEY=VALUE loader (stdlib) — no python-dotenv dependency."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def entry_id(source: dict) -> str:
    if source.get("soundcloud_id"):
        return "sc-" + str(source["soundcloud_id"])
    if source.get("youtube_id"):
        return "yt-" + str(source["youtube_id"])
    url = source.get("soundcloud_url") or source.get("youtube_url") or source.get("url") or ""
    return "src-" + (url.rstrip("/").rsplit("/", 1)[-1] or "unknown")


def parse_title(raw_title: str) -> dict:
    """Deterministic metadata from a raw title (reuses scripture.py primitives)."""
    scr = parse_scripture(fold(raw_title), raw_title)
    spk = parse_speaker(raw_title)
    return {
        "raw_title": raw_title,
        "title": clean_title(raw_title, scr, spk),
        "language": "en" if (scr and scr["is_english"]) else "fr",
        "date": date_prefix(raw_title),
        "speaker": spk,
        "series_part": parse_part(raw_title),
        "scripture_osis": scr["osis"] if scr else None,
        "scripture_display": scr["display"] if scr else None,
        "scripture_book": scr["book_osis"] if scr else None,
        "scripture_chapter": scr["chapter"] if scr else None,
        "kind": classify(raw_title),
    }


def build_entry(source: dict, *, transcribe, enrich,
                transcripts_dir=TRANSCRIPTS, persist_transcript=True) -> dict:
    raw_title = source.get("raw_title")
    if raw_title is None:
        raise ValueError("source needs raw_title (auto-fetch not wired in this build)")

    eid = entry_id(source)
    parsed = parse_title(raw_title)

    result = transcribe(source)                      # external step 1 (injected)
    # The real transcriber returns {text, vtt, segments, language}; fakes/legacy may
    # return a plain string. Normalize so enrichment + persistence handle both.
    tr = {"text": result} if isinstance(result, str) else (result or {})
    text = tr.get("text") or ""
    enrichment = enrich(text, parsed) or {}          # external step 2 (injected)

    transcript_ref = captions_ref = segments_ref = None
    if persist_transcript and text:
        transcripts_dir = Path(transcripts_dir)
        transcripts_dir.mkdir(parents=True, exist_ok=True)

        def _persist(ext, content):
            path = transcripts_dir / f"{eid}.{ext}"
            path.write_text(content, encoding="utf-8")
            return str(path.relative_to(ROOT)) if ROOT in path.parents else str(path)

        transcript_ref = _persist("txt", text)
        if tr.get("vtt"):                            # subtitle-ready segment timestamps
            captions_ref = _persist("vtt", tr["vtt"])
        if tr.get("segments"):                       # word-level timing + confidence (#42)
            segments_ref = _persist("json", json.dumps(
                {"language": tr.get("language", "fr"), "segments": tr["segments"]},
                ensure_ascii=False))

    return {
        "id": eid,
        "source": ("soundcloud" if source.get("soundcloud_id") or source.get("soundcloud_url")
                   else "youtube"),
        "raw_title": raw_title,
        "title": parsed["title"],
        "language": parsed["language"],
        "date": parsed["date"],
        "speaker": parsed["speaker"] or enrichment.get("speaker_hint") or None,
        "series_part": parsed["series_part"],
        "series_hint": enrichment.get("series_hint") or None,
        "scripture_osis": parsed["scripture_osis"],
        "scripture_display": parsed["scripture_display"],
        "scripture_book": parsed["scripture_book"],
        "scripture_chapter": parsed["scripture_chapter"],
        "primary_scripture": enrichment.get("primary_scripture") or parsed["scripture_display"],
        "scripture_refs": enrichment.get("scripture_refs") or [],
        "topics": enrichment.get("topics") or [],
        "summary": enrichment.get("summary") or None,
        "transcript_ref": transcript_ref,
        "captions_ref": captions_ref,
        "segments_ref": segments_ref,
        "kind": parsed["kind"],
        "media": {
            "soundcloud_id": source.get("soundcloud_id"),
            "youtube_id": source.get("youtube_id"),
            "soundcloud_url": source.get("soundcloud_url"),
            "youtube_url": source.get("youtube_url"),
        },
    }


def _cli():
    import argparse
    ap = argparse.ArgumentParser(description="Build one catalog entry from a YT/SC source.")
    ap.add_argument("--soundcloud-url"); ap.add_argument("--soundcloud-id")
    ap.add_argument("--youtube-url"); ap.add_argument("--youtube-id")
    ap.add_argument("--raw-title", required=True)
    ap.add_argument("--model", default="claude-sonnet-4-6")
    args = ap.parse_args()
    load_dotenv()  # pick up ANTHROPIC_API_KEY (+ optional SERMO_* overrides) from .env
    source = {k: v for k, v in {
        "soundcloud_url": args.soundcloud_url, "soundcloud_id": args.soundcloud_id,
        "youtube_url": args.youtube_url, "youtube_id": args.youtube_id,
        "raw_title": args.raw_title,
    }.items() if v}
    from transcribe import make_transcriber
    from enrich import make_enricher
    entry = build_entry(source, transcribe=make_transcriber(), enrich=make_enricher(model=args.model))
    print(json.dumps(entry, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    _cli()
