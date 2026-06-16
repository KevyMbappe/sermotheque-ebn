#!/usr/bin/env python3
"""
Sermothèque EBN — production enrichment runner (the catalog-wide pass).

Drives `build_entry` over many sermons: download → transcribe (mlx-whisper) → enrich
(Claude) → `save_entry` into the enrichment store (#44). Built for an unattended
multi-hour run:
  • RESUMABLE — skips any sermon already in the enrichment store, so a crash/kill at
    #300 resumes from #300 (each sermon is durable the moment it's stored).
  • LOGFILE — appends one line per sermon (id, time, tokens, cost, running total) to
    logs/enrichment.log, plus live progress on stderr.
  • COST — live per-sermon and cumulative, from real token usage × the model's price.
At the end it runs the writeback so catalog.json/.csv reflect the new enrichment.

Examples:
  ./.venv/bin/python pipeline/run_enrichment.py --source soundcloud           # the 239 SC spine
  ./.venv/bin/python pipeline/run_enrichment.py --source all --limit 5         # smoke test
  ./.venv/bin/python pipeline/run_enrichment.py --ids sc-123,yt-abc --model claude-haiku-4-5
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from build_entry import build_entry, load_dotenv
from transcribe import make_transcriber, YTDLP, CACHE
from enrich import make_enricher, cost_of
from enrichment_store import save_entry, load_store, writeback, STORE

ROOT = Path(__file__).resolve().parent.parent
CAT = ROOT / "data" / "catalog" / "catalog.json"
LOG = ROOT / "logs" / "enrichment.log"
SC_CHANNEL = "https://soundcloud.com/ebn-paris/tracks"
SC_URL_CACHE = CACHE / "sc_urls.tsv"


def select_targets(rows, done_ids, *, source="soundcloud", ids=None, limit=None):
    """Pure: which catalog rows to enrich. Filters by source, honors an explicit id list,
    skips anything already enriched (resume), and caps at `limit`. Returns a list of rows."""
    want = set(ids) if ids else None
    out = []
    for r in rows:
        if want is not None and r["id"] not in want:
            continue
        if source != "all" and r.get("source") != source:
            continue
        if r["id"] in done_ids:
            continue
        out.append(r)
    return out[:limit] if limit else out


def soundcloud_url_map(verbose=True):
    """id -> permalink for the SoundCloud channel (cached). yt-dlp writes a literal '\\t'."""
    if not SC_URL_CACHE.exists():
        if verbose:
            print(f"• fetching SoundCloud URL map ({SC_CHANNEL}) …", file=sys.stderr, flush=True)
        CACHE.mkdir(parents=True, exist_ok=True)
        res = subprocess.run([YTDLP, "--flat-playlist", "--no-warnings",
                              "--print", "%(id)s\t%(webpage_url)s", SC_CHANNEL],
                             check=True, capture_output=True, text=True)
        SC_URL_CACHE.write_text(res.stdout, encoding="utf-8")
    m = {}
    for line in SC_URL_CACHE.read_text(encoding="utf-8").splitlines():
        line = line.replace("\\t", "\t")
        if "\t" in line:
            i, u = line.split("\t", 1)
            m[i] = u
    return m


def source_for(row, sc_map):
    """Build the build_entry `source` dict (with a downloadable URL) for a catalog row."""
    media = row.get("media") or {}
    src = {"raw_title": row["raw_title"], "upload_date": (row.get("date") or "").replace("-", "")}
    if media.get("youtube_id"):
        src["youtube_id"] = media["youtube_id"]
        src["youtube_url"] = f"https://www.youtube.com/watch?v={media['youtube_id']}"
    if media.get("soundcloud_id"):
        src["soundcloud_id"] = media["soundcloud_id"]
        url = sc_map.get(media["soundcloud_id"])
        if url:
            src["soundcloud_url"] = url
    return src


def main():
    ap = argparse.ArgumentParser(description="Catalog-wide enrichment pass.")
    ap.add_argument("--source", choices=["soundcloud", "youtube", "all"], default="soundcloud")
    ap.add_argument("--ids", help="comma-separated catalog ids to restrict to")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--model", default="claude-sonnet-4-6")
    ap.add_argument("--segments", action="store_true", help="also persist word-level .json")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()
    load_dotenv()
    verbose = not args.quiet

    LOG.parent.mkdir(parents=True, exist_ok=True)
    logfh = LOG.open("a", encoding="utf-8")

    def log(msg):
        if verbose:
            print(msg, file=sys.stderr, flush=True)
        logfh.write(msg + "\n"); logfh.flush()

    rows = json.loads(CAT.read_text(encoding="utf-8"))
    done = set(load_store())
    ids = [s.strip() for s in args.ids.split(",")] if args.ids else None
    targets = select_targets(rows, done, source=args.source, ids=ids, limit=args.limit)
    sc_map = soundcloud_url_map(verbose) if any((r.get("media") or {}).get("soundcloud_id")
                                                for r in targets) else {}

    log(f"=== enrichment pass: {len(targets)} sermons (source={args.source}, model={args.model}, "
        f"{len(done)} already done) ===")
    transcribe = make_transcriber(verbose=verbose, word_timestamps=args.segments)
    total, ok, t_all = 0.0, 0, time.monotonic()

    for n, row in enumerate(targets, 1):
        src = source_for(row, sc_map)
        if not (src.get("soundcloud_url") or src.get("youtube_url")):
            log(f"[{n}/{len(targets)}] {row['id']}  SKIP (no resolvable URL)"); continue
        log(f"[{n}/{len(targets)}] {row['id']}  {row['raw_title']!r}")
        cost, t0 = {}, time.monotonic()
        try:
            entry = build_entry(
                src, transcribe=transcribe,
                enrich=make_enricher(model=args.model,
                                     on_usage=lambda i, o: cost.update(usd=cost_of(args.model, i, o), i=i, o=o)),
                on_progress=lambda p: log(f"      [{time.monotonic()-t0:5.1f}s] → {p}"),
                persist_segments=args.segments)
        except Exception as e:
            log(f"      FAILED: {e!r}"); continue
        save_entry(entry, model=args.model)        # durable now — resume skips it next time
        c = cost.get("usd", 0.0); total += c; ok += 1
        log(f"      ✓ {time.monotonic()-t0:.0f}s · {cost.get('i',0):,}+{cost.get('o',0)} tok · "
            f"${c:.4f} · running total ${total:.4f}")

    merged = writeback()                            # reflect new enrichment in catalog.json/.csv
    log(f"=== done: {ok}/{len(targets)} enriched · ${total:.4f} · {(time.monotonic()-t_all)/60:.0f} min "
        f"· catalog now has {merged} enriched rows ===")


if __name__ == "__main__":
    main()
