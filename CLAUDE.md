# CLAUDE.md — Sermothèque EBN

> **Read this first.** It is the front door for any agent (or person) picking up this project. It orients you, points to the detailed specs, states what's built, and tells you how to continue.
>
> ⚠️ **Before you finish any task that advances the project, follow the [Maintenance protocol](#maintenance-protocol-keep-the-history-in-sync) at the bottom — keep the history/state files in sync.** This project's value is that its state lives in the repo, not in an agent's memory; that only holds if every contributor updates these files.

## What this project is

Software for **Église Bonne Nouvelle** (église réformée baptiste, Poissy, France — site: https://www.eglisebonnenouvelle.com, WordPress). The church records sermons on **YouTube** (`@eglisebonnenouvelle855`) and **SoundCloud** (`soundcloud.com/ebn-paris`).

**North star:** *The catalog is the asset; every app, site, and platform is a replaceable window onto it.* So the **primary project is a durable, portable system of record for the church's preaching** — a rich sermon/service database + the pipeline that feeds it. Apps (mobile/TV) and the website are downstream consumers, built later.

This reframe happened through a long planning conversation; the **two spec docs below are the source of truth**, and their decision logs capture *why* each choice was made.

## Document map

| File | What it is |
|---|---|
| **docs/SERMOTHEQUE.md** | ★ The primary project: sermon/service system-of-record spec (architecture, canonical schema, pipeline, backfill, roadmap, decisions). |
| **docs/PRD.md** | The app suite (web/mobile/TV) — now a *downstream consumer* of the catalog. Full decision log. |
| **docs/ENRICHMENT-MODEL.md** | Live reference: Haiku-vs-Sonnet bake-off, measured per-sermon cost, Claude pricing table. Consult before the full enrichment pass. |
| **CLAUDE.md** | This file — orientation + current state. |
| `pipeline/scripture.py` | Shared parsing primitives (OSIS book map, scripture/speaker/series parsing). Imported by the others. Also holds **`parse_reference` / `normalize_refs` (#56)** — citation-style FR/EN text → OSIS ids, for the in-body `scripture_refs`. |
| `pipeline/parse_catalog.py` · `match_youtube.py` · `fold_orphans.py` · `cluster_series.py` · `enrichment_store.py` | **Catalog-build** pipeline (batch, pure-stdlib). `build.py` runs them in order, ending with the enrichment **writeback** (#44). |
| `pipeline/build_entry.py` | ★ **Single entry point**: `build_entry(source, *, transcribe, enrich)` — one YT/SC source → one canonical entry. |
| `pipeline/run_enrichment.py` | **Production runner** for the catalog-wide pass: resumable, logfile, live cost; `save_entry` per sermon → store + writeback (#44/#45). |
| `pipeline/transcribe.py` · `enrich.py` · `embed.py` | The three **injected** external steps: mlx-whisper adapter (+ `clean_transcript`), Claude-API adapter, and the Resemblyzer **voiceprint** adapter (#46). |
| `pipeline/enrichment_store.py` · `voiceprint_store.py` | Id-keyed stores: enrichment (#44, text-derived, writeback) and voiceprints (#46, audio-derived, captured in-pass by `build_entry`). |
| `pipeline/schema.py` | **Frozen canonical record contract (#53):** the catalog-row field spec (types, required/optional) + stdlib validator + emits `data/catalog/sermon.schema.json` (the WP-import contract). Drift guard ties it to `CANON` + `ENRICHMENT_FIELDS`; `build.py` validates last. |
| `pipeline/speaker_id.py` | **Audio speaker attribution (#49):** centroids from title-confirmed voiceprints → cosine nearest-centroid → `speakers.json` + writeback (ladder: human > title > audio-fingerprint > default-rule). `speaker_overrides.json` = human-confirmed labels. (`fingerprint.py` is the weaker text-only Tier A, kept as a review flag.) |
| `tests/` | Stdlib `unittest` suite (offline). Run: `python3 -m unittest discover -s tests`. |
| `apps/web-poc/` | **WIP (#54)** — first *consumption* surface: static React 18 + Vite 6 app (elder demo + de-risks the WP library; it does not replace it). `scripts/build-data.mjs` projects `data/catalog/` → `public/data/` before every dev/build (enriched rows + VTT), so the site can't drift from the committed dataset. Pages Home/Browse/Book/Sermon; VTT-synced transcript, chapter deep-links, **shareable timestamped URLs** (`?t=`), **per-sermon pre-rendered pages** for link previews, and **browse-by-passage** over the OSIS citations (#56) — 54 books vs 22 preached. Publishes 131 of the 139 enriched. Mobile layout measured clean 320→768 px; chapter→player seek confirmed on desktop. **LIVE: https://kevymbappe.github.io/sermotheque-ebn/** (auto-redeploys on `data/catalog/**` changes). |
| `docs/plans/WEB-POC.md` · `WEB-POC-STATUS.md` | The web POC's plan and its **resume note** — exactly what's done, what's left, and the known traps. Read `WEB-POC-STATUS.md` before touching `apps/web-poc/`. |
| `tools/md_to_pdf.py` | Markdown → PDF via headless Chrome (used for SYNTHESE / spike PDFs). |
| `docs/research/` | **Historical evidence** (not living docs): the M3 ASR spike (`METHODOLOGY.md`, `RESULTS.md`/`.pdf`) + the M5b POC (`POC.md`/`.pdf`, `poc_entries.json`) + `spike-transcripts/` (the original slices the spike ran on). |
| `data/raw/*.tsv` | Raw inventories pulled via `yt-dlp`. `data/catalog/` = canonical dataset (`catalog.json`/`.csv`, `series.json`, `youtube_orphans.json`, `enrichment.json` [#44], `voiceprints.json` [id-keyed speaker embeddings, #46], `transcripts/`). |
| `data/catalog/transcripts/` | Canonical transcripts, **named `<entry-id>.<ext>`** (the `id` from `catalog.json`): `sc-<id>.txt` (cleaned) + `.raw.txt` (uncleaned ASR — accent signal for speaker ID, #45) + `.vtt` (segment timing) committed by default; `.json` (word-level timing) is opt-in via `--segments` (heavy — see #42); later `.en.vtt` / `.pt.vtt` for translated subtitles. Filename = primary key; title/date live in the catalog, not the filename. |

## Architecture (three layers)

```
AUTHORING (write)  WordPress admin (humans) + the pipeline (machines)  — replaceable
      ▼ write Sermon/Service records
CANONICAL (own) ★  clean, app-agnostic, git-versioned dataset + Catalog API + search  — the durable asset
      ▼ everything reads from here
CONSUMPTION (read) website sermon library · mobile/TV apps · YouTube thumbnail pusher  — replaceable
```
WordPress **authors but does not own**. The canonical dataset (this repo's `data/`) is the source of truth and survives any shell.

## Key decisions (the short list — full logs in the specs)

- **System of record:** WP authors → canonical = portable, git-versioned dataset. (Build custom, not a turnkey vendor.)
- **SoundCloud is the catalog spine** (its titles are 74% structured vs 20% on YouTube). Match YouTube videos *in* by title/date.
- **Scripture:** canonical **OSIS** IDs + FR/EN parser → browse-by-book.
- **Transcripts:** ASR (Whisper-class) on clean SoundCloud audio is the *metadata engine* (auto-suggest topics/summary/scripture); correct opportunistically. **ASR backend is pluggable** (decision #41): mlx-whisper local on Mac for the backfill, cloud Whisper API (e.g. Groq) for the church's Windows machines in production — same injected `transcribe_fn` contract. **Timestamps captured in the same pass** (decision #42): each sermon yields `.txt` (plain) + `.vtt` (subtitle-ready segment timing) + `.json` (word-level timing + confidence) — free at ASR time, and the basis for EN/PT subtitles, deep-linking, and search-to-moment.
- **Enrichment model: Sonnet-only** (decision #53 — Haiku 4.5 was reconsidered as a budget path for the YouTube bulk and **rejected** on French/theological precision; it is no longer a fallback). Claude **`claude-sonnet-4-6`**, measured **$0.0705/sermon** over the 30-sermon checkpoint ⇒ **~$36 for all 517** (~$27 for the 378 still unenriched).
- **Capture ≠ enrich** (decision #52 — the split that governs how the backfill is run): the **audio** pass (download → ASR → voiceprint) is the *one-shot, irreversible, $0-API* work and must be banked once; everything **text**-derived is re-runnable forever from the committed transcripts. Hence two passes: `--no-enrich` to capture, then enrich at any cadence.
- **First consumption surface:** `apps/web-poc/` (decision #54, **provisional/WIP**) — a static app that consumes the catalog by *build-time projection*, no API, no server. Whether it or the WordPress import is the real first public deliverable is **not yet decided**.
- **In-body citations are normalised, not rewritten** (decision #56): the LLM's free-text `scripture_refs` ("Jean 1:1,14") is kept as the display half and gets a **derived** twin `scripture_refs_osis` (`John.1.1`, `John.1.14`) as the queryable half. It is **recomputed by the writeback on every build**, never stored — so improving `scripture.parse_reference` improves the whole catalog at **zero API cost**.
- **Topics:** curated vocabulary, AI-bootstrapped; labels FR/EN/PT.
- **EN/FR conference versions:** independent records linked by `translation_of`.
- **Audit:** git history of the export. **Search:** prebuilt static index (no server).
- **Two content types:** rich `Sermon` (full engine) + light `Service` (full Sunday recording, ~2 h, "Culte Dimanche DD/MM").
- **Apps (later):** Expo React Native, iOS + Android + Android TV + Fire TV first (Apple TV fast-follow); French/EN/PT UI; no accounts v1; giving = link to WP; privacy-first analytics. Operability is first-class (church-owned accounts; media team = Publisher role; runbook + named backup).

## Measured inventory (yt-dlp, 2026-06-13 — in `data/`)

- YouTube **Videos** (cut sermons): **300** · YouTube **Live** (services): **102** · SoundCloud (clean sermon audio): **239**.
- First-pass parse of the 239 SC titles: **82% scripture (OSIS)** (196/239), 87% clean title. Across the built union: **215/517 (42%)** carry an OSIS ref, over **28** Bible books (YouTube titles are far less structured — only 19/278).
- **26 series** auto-clustered over the union: Galates 71, Hébreux 28, Jacques 14, Genèse 13, Ézéchiel 11, + thematic (Joie chrétienne, Noël…, Fruit de l'Esprit).
- **Catalog state (2026-07-30, counted from `data/`):** 517 rows · **139 transcribed** (`.txt`+`.vtt`, 130 `.raw.txt`) · **217 voiceprints** · **139 enriched** (126 SC / 13 YT) · speakers 100 audio-fingerprint / 45 title / 331 default-rule / 41 blank · languages 491 fr / 26 en · kinds 490 sermon / 12 teaching / 9 teaching-or-qa / 6 qa · 123 tests green.
- **In-body scripture citations (2026-08-01, #56):** the 139 enriched rows carry **1 243 free-text citations**, now normalised to **`scripture_refs_osis`** — **1 243/1 243 parsed, 0 failures**, 1 248 OSIS ids, 923 distinct, **380 distinct book+chapter keys**. **54 distinct Bible books** are reachable through body citations, against **22** via the main passage on those same rows (28 across all 517). Ready for an inverted index (`Rom.8` → sermons) / browse-by-passage.
- **YouTube ≠ SoundCloud mirror** (matcher finding): they are largely **complementary**. After hardening the matcher (decision #43 — duration only corroborates, title/scripture must carry the match): **18** confirmed same-language overlaps + **4** EN↔FR translations; **278 YT videos are net-new**. **True catalog = 517 distinct sermons** (239 SC + 278 YT-only). Orphans (parsed) in `data/catalog/youtube_orphans.json`. *(Earlier "61 overlaps / 467 union" was inflated by ~43 duration-collision false positives — see #43.)*
- **ASR enrichment validated** (spike, `docs/research/METHODOLOGY.md`): mlx-whisper `large-v3-turbo` transcribes French sermons ~6× real-time locally; LLM topics/summary are confirm-don't-type quality. **Title → scripture; transcript → topics/summary/series/search.** Speaker inference needs a default rule, not ASR.

## How to run the pipeline

```bash
python3 pipeline/build.py             # runs the whole pipeline in order (recommended)

# order (build.py does this): parse → match → fold → cluster → writeback
python3 pipeline/parse_catalog.py     # SoundCloud titles -> data/catalog/catalog.json (239)
python3 pipeline/match_youtube.py     # link YT videos (corroborated, #43); write youtube_orphans.json
python3 pipeline/fold_orphans.py      # fold orphans -> unified catalog (517, canonical schema)
python3 pipeline/cluster_series.py    # series over the union + write series.json + catalog.csv
python3 pipeline/enrichment_store.py  # writeback: merge data/catalog/enrichment.json onto the catalog (#44)
```
Re-pulling inventories needs a recent yt-dlp (≥2026.x for YouTube's layout); the TSVs use a **literal `\t`** separator (yt-dlp didn't expand the escape) — the loaders handle this with `line.replace("\\t","\t")`.

**Enrichment pipeline** (per-sermon, M5):
```bash
python3 -m unittest discover -s tests        # 34 tests, offline, pure stdlib — no venv needed

# one-time setup (everything project-local & gitignored):
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
cp .env.example .env        # then put your ANTHROPIC_API_KEY in .env

# one sermon (uses the .venv python so anthropic/yt-dlp/mlx-whisper are importable; auto-loads .env):
./.venv/bin/python pipeline/build_entry.py --youtube-url <url>   # --raw-title optional (fetched)

# the catalog-wide pass (resumable, logfile, live cost — the real backfill):
./.venv/bin/python pipeline/run_enrichment.py --source soundcloud   # 239 SC spine, ~16h, ~$15
./.venv/bin/python pipeline/run_enrichment.py --source all --limit 3 # smoke test first
# capture-only (the irreversible one-shot, $0 API): transcribe + voiceprint, enrich later from disk
./.venv/bin/python pipeline/run_enrichment.py --source all --no-enrich   # bank transcripts+voiceprints (#52)
```
Everything the pipeline needs lives **inside the project** (never `/tmp`):
- **`.venv/`** (gitignored) — yt-dlp ≥ 2026.x, mlx-whisper, anthropic (see `requirements.txt`). `transcribe.py` defaults to `.venv/bin/*` (override via `SERMO_YTDLP` / `SERMO_MLX_WHISPER`).
- **`cache/`** (gitignored) — downloaded audio + scratch; audio is deleted after transcription.
- **`.env`** (gitignored; template `.env.example`) holds `ANTHROPIC_API_KEY` for the enrich step (model `claude-sonnet-4-6`, measured **$0.0705/sermon**; Sonnet-only per #53) — the CLI auto-loads it. Without a key the deterministic steps still run; inject your own `enrich` fn. *(`.venv` ≈ node_modules ← `requirements.txt`; `.env` ≈ Node's `.env` ← `.env.example`.)*
- The only thing *outside* the project is the Whisper model (~1.6 GB) in the standard `~/.cache/huggingface` shared ML cache — conventional and persistent, not scratch.
- Nothing critical is unrecoverable: the pipeline is committed, audio re-downloadable, transcripts regenerable.

## Current status & next steps

**Done:** planning/specs · M1 catalog · M1b series · M2 YT↔SC matching · M2b duration dedup (union 467) · M3 ASR+LLM spike (PASS) · M3b n=8 sample · M4 fold→unified 467 · **M5 enrichment pipeline `build_entry`** · M5b POC (8 real sermons) · M5c cost + Haiku-vs-Sonnet bake-off · M5d timestamp capture · M5e docs restructure · **M5f pipeline hardening (cap 120k, YT date, live tracking + cost, txt+vtt default) + first real YT run** · **M5h matcher hardening (false positives fixed; union 467→517)** · **M5i enrichment writeback (#44)** · **M5j production runner + default-speaker rule (#45)** · **M5k/l audio voiceprint validated + rich schema (#46)** · **M5m voiceprint capture adapter** · **M5n 30-sermon checkpoint (#47, store→39, ~$0.0705/sermon)** · **M5o language-from-audio + retry-on-garbage (#48)** · **M5p–q audio speaker attribution + series priors (#49–#52: all 5 voices, 100 rows audio-fingerprint, LOO 99%)** · **M5s capture/enrich decoupled + rebuild integrity (#52)** · **M5t frozen record contract + Sonnet-only (#53)** · **M5u capture batch (139 transcripts + 217 voiceprints banked, $0 API — paused at ~27%)** · **M5v enrich-from-disk (store 39→139, no re-ASR)** · **M6a POC web WIP (#54)** · **M6b/c POC web deployed (#55)** · **M5w in-body citations → OSIS (#56)** · 123 tests · git + GitHub remote.

Catalog is the **unified union of 517 records** (239 SoundCloud + 278 YouTube-only), one canonical schema with `source` + `media`, 26 series, schema-validated (#53). **Enrichment persists across rebuilds** via an id-keyed store (`data/catalog/enrichment.json`) + writeback in `build.py` (#44).

**Where the backfill actually stands (2026-07-30):** **139/517 transcribed (~27%)**, **217 voiceprints**, **139/517 enriched (~27%)** — 126 SoundCloud, 13 YouTube. The two-pass split (#52) worked exactly as designed: a capture pass banked the audio artifacts at **$0 API** (2026-06-20), then an enrich pass added 100 sermons **from disk, with no re-ASR** (2026-06-22). **The capture pass then stopped and has not been resumed** — 378 sermons still have no transcript. Speaker attribution after writeback: 100 `audio-fingerprint` / 45 `title` / 331 `default-rule` / 41 blank.

⚠️ **Integrity gap to audit before resuming:** **79 ids hold a voiceprint but no committed transcript** (59 SC / 20 YT) — yet `build_entry` writes both from the same download. Either those runs died between the two writes, or the transcripts were never committed. Capture-mode resumability keys "done" off *the transcript on disk*, so as-is those 79 get re-downloaded and re-ASR'd (correct, but hours of wasted compute).

Two text-layer findings from the M5n checkpoint remain open (#47), **neither blocking** (both re-runnable from committed transcripts, no re-ASR): EN sermons lose timestamp-anchoring (French anchors vs English VTT); short clips fabricate structure.

**Language + speaker now audio-truthful (#48/#49, 2026-06-17).** Chasing the EN finding exposed a root cause: ASR hard-coded `--language fr` → genuinely-non-French audio became `...` garbage + title-hallucinated enrichment, and the title-derived `language` label was unreliable. Fixed: forced-fr default → **retry-en on garbage** → label from **transcript content**; plus mlx stale-output clear, YouTube download retry/back-off, and source-language anchors. **Speaker attribution wired** (`speaker_id.py`): cosine nearest-centroid over the captured voiceprints (LOO 10/10) → **15 rows upgraded to `audio-fingerprint`**, incl. the Ézéchiel/Leçon sermons correctly reassigned to **Stephan**. Ladder: human > title > audio-fingerprint > default-rule (audio fixes default-rule/blank, flags title conflicts). David's 2-example centroid is the bottleneck → bootstrap via `speaker_overrides.json`.

**Open / next (pick up here — in priority order):**

1. ★ **Audit the 79 voiceprint-without-transcript ids, then RESUME the capture pass.** This is the critical path and **the only irreversible work in the project** — every other task is re-runnable from what's committed. `./.venv/bin/python pipeline/run_enrichment.py --source all --no-enrich` (resumable, $0 API, skips anything already on disk). **Requires Apple Silicon** — mlx-whisper is Mac-only (#41), so this cannot run in a Linux container or CI; it's local work on the Mac. 378 sermons left ≈ several overnight runs at ~15× real-time. Do SoundCloud first (flawless in every batch so far); YouTube is the flaky path (403 throttling, retry/back-off is in).
2. **Enrich the remaining 378** — reads the committed transcripts, **no re-ASR** (#52): `run_enrichment.py --source all`. Sonnet-only (#53), **~$0.0705/sermon ⇒ ~$27** for what's left. Needs `ANTHROPIC_API_KEY`. Can run anywhere, at any cadence, including in chunks — and only for sermons already captured in (1).
3. **Polish the web POC — it is LIVE** at **https://kevymbappe.github.io/sermotheque-ebn/** (#54/#55, M6c, 2026-08-01): 131 enriched sermons, player + chapter deep-links + synced transcript, mobile-clean 320→768 px, and it **republishes itself** whenever `data/catalog/**` changes. It remains a **demo for the elders + de-risking of the WordPress library**, not a replacement. Left: the **YouTube IFrame path** (a distinct code path, never exercised — the dev container blocks YouTube) and an EN sermon. Resume notes: `docs/plans/WEB-POC-STATUS.md`.
4. **Resolve the stray `Sermothèque EBN/` Xcode project** at the repo root — an untouched default SwiftUI template (12 files, `ContentView.swift`/`Item.swift`). A native iOS target contradicts **PRD #9 (Expo/React Native)**. Delete it, or write the decision that supersedes #9.
5. **Build the inverted scripture index** now that `scripture_refs_osis` exists (#56) — `Rom.8` → the sermons that cite it, book/chapter browse. Pure derivation from the committed catalog: no API, no re-ASR, runs anywhere.
6. **Close the #47 text-layer findings** when convenient — EN timestamp-anchoring and short-clip fabrication; both fixable from committed transcripts, no re-ASR.
- *(Optional: also fold the 102 Live `Service` records in — currently only the Videos-tab orphans are folded.)*

**Still-open design questions:** SoundCloud trim (only the sermon, or intro/offering too?), canonical hosting location, dedup edge cases (multi-part, re-uploads), web POC vs WP import (#54). See docs/SERMOTHEQUE.md §8.

## Conventions

- Content is French-dominant; some English conference sermons exist (add `language`, default `fr`). UI (future apps) is FR/EN/PT.
- **Catalog-build scripts + the pipeline core + tests are pure-stdlib Python 3.** Only the *real adapters* (`transcribe.py` → yt-dlp/mlx-whisper via subprocess; `enrich.py` → `anthropic`) need external tools, and they lazy-load so the core imports without them.
- This is a real church's data — keep titles/names accurate; French theological/biblical naming matters (e.g. "Épître **de** Jacques", not "à").

## Maintenance protocol (keep the history in sync)

**Do this before you finish any task that advances the project.** The repo *is* the project's memory — these files must always reflect reality.

**State/history files to keep in sync:**
- `CLAUDE.md` — *Current status & next steps*, *Measured inventory*, *Key decisions*.
- `README.md` — the **Status** table and the **Roadmap** checklist.
- `docs/SERMOTHEQUE.md` — the **Build log** (§7b), **decision log**, resolved/open questions; bump *Last updated*.
- `docs/PRD.md` — its **decision log** and status; bump *Last updated*.

**When you complete a step** (milestone, new script, pipeline change):
1. Tick the roadmap box(es) in `README.md` **and** `SERMOTHEQUE.md`.
2. Add a dated entry to the **Build log** in `docs/SERMOTHEQUE.md` (what changed + any coverage/count numbers).
3. Update *Current status & next steps* in `CLAUDE.md` — move the item from "next" to "done" and name the new next step.
4. If counts/coverage changed, update the numbers in both `CLAUDE.md` and the `README.md` status table.
5. If you changed the pipeline, **re-run it** so `data/` reflects reality before committing.

**When a decision is made or changed:**
1. Append a numbered entry to the decision log in the relevant spec (`docs/SERMOTHEQUE.md` or `docs/PRD.md`).
2. Edit the affected sections to match; if it **supersedes** an earlier decision, say so explicitly (don't silently leave stale text).
3. Reflect it in `CLAUDE.md` *Key decisions* if significant.

**Always:**
- Use **absolute dates** (e.g. `2026-06-13`), never "today".
- Commit with a clear message ending in the trailer `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`, then **push to `origin`**.
- Leave the tree consistent: specs, README, and `data/` should never contradict each other in a commit.
