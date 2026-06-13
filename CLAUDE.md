# CLAUDE.md — Sermothèque EBN

> **Read this first.** It is the front door for any agent (or person) picking up this project. It orients you, points to the detailed specs, states what's built, and tells you how to continue. Keep it updated as the project moves.

## What this project is

Software for **Église Bonne Nouvelle** (église réformée baptiste, Poissy, France — site: https://www.eglisebonnenouvelle.com, WordPress). The church records sermons on **YouTube** (`@eglisebonnenouvelle855`) and **SoundCloud** (`soundcloud.com/ebn-paris`).

**North star:** *The catalog is the asset; every app, site, and platform is a replaceable window onto it.* So the **primary project is a durable, portable system of record for the church's preaching** — a rich sermon/service database + the pipeline that feeds it. Apps (mobile/TV) and the website are downstream consumers, built later.

This reframe happened through a long planning conversation; the **two spec docs below are the source of truth**, and their decision logs capture *why* each choice was made.

## Document map

| File | What it is |
|---|---|
| **SERMOTHEQUE.md** | ★ The primary project: sermon/service system-of-record spec (architecture, canonical schema, pipeline, backfill, roadmap, decisions). |
| **PRD.md** | The app suite (web/mobile/TV) — now a *downstream consumer* of the catalog. Full decision log (#1–36). |
| **CLAUDE.md** | This file — orientation + current state. |
| `scripts/parse_catalog.py` | Parses SoundCloud titles → structured metadata (OSIS scripture, speaker, series part, language, kind). |
| `scripts/cluster_series.py` | Groups sermons into ordered series (run AFTER the parser). |
| `data/*.tsv` | Raw inventories pulled via `yt-dlp` (YouTube videos/streams, SoundCloud tracks). |
| `data/catalog.json` / `.csv` | The structured sermon catalog (canonical, versioned). |
| `data/series.json` | The series list. |

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

## How to run the pipeline

```bash
python3 scripts/parse_catalog.py      # data/soundcloud_tracks.tsv -> data/catalog.json/.csv
python3 scripts/cluster_series.py      # enriches catalog.json + writes data/series.json
```
Re-pulling inventories needs a recent yt-dlp (≥2026.x for YouTube's layout); the TSVs use a **literal `\t`** separator (yt-dlp didn't expand the escape) — the parser handles this with `line.replace("\\t","\t")`.

## Current status & next steps

**Done:** planning/specs · M1 first-pass catalog · M1b series clustering · git initialized (branch `main`).

**Open / next (pick up here):**
1. **YT↔SC matching** — link the 300 YouTube videos to the 239 SoundCloud sermons (fuzzy title + date), attach video to each record, flag orphans.
2. **ASR + LLM enrichment spike** — prove on ONE sermon that transcribe→suggest gives "confirm-don't-type" quality (topics/summary/scripture + infer the regular preacher, untagged in titles). *Biggest unproven assumption.*
3. **JSON Schema + WP import** — freeze the canonical record contract; design the WordPress CPT/ACF import → first public deliverable (website sermon library).

**Still-open design questions:** SoundCloud trim (only the sermon, or intro/offering too?), canonical hosting location, dedup edge cases (multi-part, re-uploads). See SERMOTHEQUE.md §8.

## Conventions

- Content is French-dominant; some English conference sermons exist (add `language`, default `fr`). UI (future apps) is FR/EN/PT.
- Scripts are pure-stdlib Python 3, no external deps.
- This is a real church's data — keep titles/names accurate; French theological/biblical naming matters (e.g. "Épître **de** Jacques", not "à").
