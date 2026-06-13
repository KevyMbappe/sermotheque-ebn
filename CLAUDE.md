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
| **CLAUDE.md** | This file — orientation + current state. |
| `pipeline/scripture.py` | Shared parsing primitives (OSIS book map, scripture/speaker/series parsing). Imported by the others. |
| `pipeline/parse_catalog.py` | SoundCloud titles → structured metadata. |
| `pipeline/cluster_series.py` | Groups sermons into ordered series (run AFTER the parser). |
| `pipeline/match_youtube.py` | Links YouTube videos to SC sermons; writes orphans. |
| `pipeline/build.py` | Runs all three in order (one command). |
| `data/raw/*.tsv` | Raw inventories pulled via `yt-dlp` (YouTube videos/streams, SoundCloud tracks). |
| `data/catalog/` | The canonical dataset: `catalog.json` / `.csv`, `series.json`, `youtube_orphans.json`. |

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
- **Transcripts:** ASR (Whisper-class) on clean SoundCloud audio is the *metadata engine* (auto-suggest topics/summary/scripture); correct opportunistically.
- **Topics:** curated vocabulary, AI-bootstrapped; labels FR/EN/PT.
- **EN/FR conference versions:** independent records linked by `translation_of`.
- **Audit:** git history of the export. **Search:** prebuilt static index (no server).
- **Two content types:** rich `Sermon` (full engine) + light `Service` (full Sunday recording, ~2 h, "Culte Dimanche DD/MM").
- **Apps (later):** Expo React Native, iOS + Android + Android TV + Fire TV first (Apple TV fast-follow); French/EN/PT UI; no accounts v1; giving = link to WP; privacy-first analytics. Operability is first-class (church-owned accounts; media team = Publisher role; runbook + named backup).

## Measured inventory (yt-dlp, 2026-06-13 — in `data/`)

- YouTube **Videos** (cut sermons): **300** · YouTube **Live** (services): **102** · SoundCloud (clean sermon audio): **239**.
- First-pass parse of the 239 SC titles: **82% scripture (OSIS)**, 87% clean title, 24 Bible books.
- **22 series** auto-clustered: Galates 69, Hébreux 28, Jacques 14, Genèse 13, Ézéchiel 11, + thematic (Joie chrétienne, Noël…, Fruit de l'Esprit).
- **YouTube ≠ SoundCloud mirror** (matcher finding): they are largely **complementary**. With full SC duration coverage (239/239) and a **duration fingerprint** (YT runs ~+51 s vs SC, calibrated) on top of title/scripture: **61** confirmed same-language overlaps + **11** EN↔FR translations; **228 YT videos are net-new** (conference ~45, English ~21, SC-absent French ~162). **True catalog = 467 distinct sermons** (union). Orphans (parsed) in `data/catalog/youtube_orphans.json`.
- **ASR enrichment validated** (spike, `docs/spike-asr-2026-06-13.md`): mlx-whisper `large-v3-turbo` transcribes French sermons ~6× real-time locally; LLM topics/summary are confirm-don't-type quality. **Title → scripture; transcript → topics/summary/series/search.** Speaker inference needs a default rule, not ASR.

## How to run the pipeline

```bash
python3 pipeline/build.py             # runs all three steps in order (recommended)

# or individually:
python3 pipeline/parse_catalog.py     # data/raw/soundcloud_tracks.tsv -> data/catalog/catalog.json/.csv
python3 pipeline/cluster_series.py    # enriches catalog.json + writes data/catalog/series.json
python3 pipeline/match_youtube.py     # links YT videos; writes data/catalog/youtube_orphans.json
```
Re-pulling inventories needs a recent yt-dlp (≥2026.x for YouTube's layout); the TSVs use a **literal `\t`** separator (yt-dlp didn't expand the escape) — the loaders handle this with `line.replace("\\t","\t")`.

## Current status & next steps

**Done:** planning/specs · M1 catalog · M1b series · M2 YT↔SC matching · M2b duration dedup (full 239/239, union 467) · M3 ASR+LLM spike (PASS) · git + GitHub remote.

**Open / next (pick up here):**
1. **Fold YT orphans into the catalog** — promote the 228 net-new videos (conference + English + SC-absent French, in `data/catalog/youtube_orphans.json`) to `Sermon`/`Service` records. Parsed already; durations available for dedup.
2. **Full ASR enrichment pass** — batch-transcribe the catalog locally (mlx-whisper turbo, ~overnight), LLM-enrich topics/summary/series; correct opportunistically. Add a default-speaker rule for untagged sermons.
3. **JSON Schema + WP import** — freeze the canonical record contract; design the WordPress CPT/ACF import → first public deliverable (website sermon library).

**Still-open design questions:** SoundCloud trim (only the sermon, or intro/offering too?), canonical hosting location, dedup edge cases (multi-part, re-uploads). See docs/SERMOTHEQUE.md §8.

## Conventions

- Content is French-dominant; some English conference sermons exist (add `language`, default `fr`). UI (future apps) is FR/EN/PT.
- Scripts are pure-stdlib Python 3, no external deps.
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
