#!/usr/bin/env python3
"""
Sermothèque EBN — voiceprint-only capture (#49 bootstrap).

A voiceprint needs only the AUDIO, not the transcript — so capturing one is far cheaper than
a full enrichment pass: download → embed → delete, with NO ASR (no thermal) and NO Claude call
(no API cost). This grows the speaker-attribution data on the cheap.

Its first job: capture the GROUND-TRUTH (title-confirmed) sermons that lack a voiceprint, so the
centroids stop being data-starved. David is named in 21 titles but only 2 had voiceprints — the
thin 2-example centroid was the attribution bottleneck (#49); this lifts it to the real count.

Resumable (skips ids already in the voiceprint store), fail-soft per sermon, logs to stderr.
Reuses the runner's URL resolution and the same injected embedder as build_entry.
"""
import argparse
import sys
import time
from pathlib import Path

import voiceprint_store
from build_entry import load_dotenv
from embed import make_embedder
from run_enrichment import soundcloud_url_map, source_for
from speaker_id import is_panel
from transcribe import CACHE, _SIDECAR_EXTS, download_audio

import json
ROOT = Path(__file__).resolve().parent.parent
CAT = ROOT / "data" / "catalog" / "catalog.json"


def select(rows, done_ids, *, ids=None, titles_only=False, limit=None):
    """Pick capture targets. --ids: explicit list. --titles-only: every title-confirmed sermon
    without a voiceprint (the ground truth for centroids). Always skips ids already captured."""
    if ids:
        want = set(ids)
        out = [r for r in rows if r["id"] in want and r["id"] not in done_ids]
    elif titles_only:
        out = [r for r in rows if r.get("speaker_provenance") == "title"
               and r["id"] not in done_ids and not is_panel(r.get("raw_title"))]
    else:
        out = [r for r in rows if r["id"] not in done_ids]
    return out[:limit] if limit else out


def main():
    ap = argparse.ArgumentParser(description="Capture voiceprints only (no ASR, no enrichment) — #49.")
    ap.add_argument("--ids", help="comma-separated catalog ids")
    ap.add_argument("--titles-only", action="store_true",
                    help="all title-confirmed sermons lacking a voiceprint (ground truth)")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()
    load_dotenv()
    verbose = not args.quiet

    def log(msg):
        print(msg, file=sys.stderr, flush=True)

    rows = json.loads(CAT.read_text(encoding="utf-8"))
    done = set(voiceprint_store.load().keys())
    ids = [s.strip() for s in args.ids.split(",")] if args.ids else None
    targets = select(rows, done, ids=ids, titles_only=args.titles_only, limit=args.limit)

    sc_map = soundcloud_url_map(verbose) if any((r.get("media") or {}).get("soundcloud_id")
                                                 for r in targets) else {}
    embed = make_embedder()
    log(f"=== voiceprint capture: {len(targets)} sermons ({len(done)} already have one) ===")

    ok = fail = 0
    for i, row in enumerate(targets, 1):
        eid = row["id"]
        src = source_for(row, sc_map)
        url = src.get("soundcloud_url") or src.get("youtube_url")
        if not url:
            log(f"[{i}/{len(targets)}] {eid}  SKIP (no resolvable url)"); fail += 1; continue
        t0 = time.monotonic()
        log(f"[{i}/{len(targets)}] {eid}  {str(row.get('speaker'))[:18]:18} {url}")
        audio = None
        try:
            audio = download_audio(url, verbose=False)
            vec = embed(audio)
            voiceprint_store.save_embedding(eid, vec)
            ok += 1
            log(f"      ✓ voiceprint captured ({time.monotonic()-t0:.0f}s)")
        except Exception as e:
            fail += 1
            log(f"      FAILED: {e!r}")
        finally:
            if audio:                                    # delete audio + any sidecars, win or lose
                base = str(Path(audio).with_suffix(""))
                for ext in (".mp3", *_SIDECAR_EXTS):
                    Path(base + ext).unlink(missing_ok=True)

    log(f"=== done: {ok} captured, {fail} failed; store now {len(voiceprint_store.load())} ===")


if __name__ == "__main__":
    main()
