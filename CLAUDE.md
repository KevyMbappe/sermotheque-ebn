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
| `pipeline/parse_catalog.py` · `match_youtube.py` · `fold_orphans.py` · `cluster_series.py` | **Catalog-build** pipeline (batch, pure-stdlib). `build.py` runs them in order. |
| `pipeline/build_entry.py` | ★ **Single entry point**: `build_entry(source, *, transcribe, enrich)` — one YT/SC source → one canonical entry. |
| `pipeline/transcribe.py` · `enrich.py` | The two **injected** external steps: mlx-whisper adapter (+ `clean_transcript`) and Claude-API adapter. |
| `tests/` | Stdlib `unittest` suite (offline). Run: `python3 -m unittest discover -s tests`. |
| `tools/md_to_pdf.py` | Markdown → PDF via headless Chrome (used for SYNTHESE / spike PDFs). |
| `docs/spike-asr/` | ASR spike evidence: `METHODOLOGY.md`, `RESULTS.md`/`.pdf`, sample `transcripts/`. |
| `data/raw/*.tsv` | Raw inventories pulled via `yt-dlp`. `data/catalog/` = canonical dataset (`catalog.json`/`.csv`, `series.json`, `youtube_orphans.json`, `transcripts/`). |

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
- **Transcripts:** ASR (Whisper-class) on clean SoundCloud audio is the *metadata engine* (auto-suggest topics/summary/scripture); correct opportunistically. **ASR backend is pluggable** (decision #41): mlx-whisper local on Mac for the backfill, cloud Whisper API (e.g. Groq) for the church's Windows machines in production — same injected `transcribe_fn` contract.
- **Enrichment model:** Claude **`claude-sonnet-4-6`**, ~**$0.06/sermon** measured (decision #40; ~$23 for the full 467). Haiku 4.5 is ⅓ the cost and nearly as good, but Sonnet wins on French precision + correct heresy naming — kept as default, Haiku is the budget fallback.
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
- **ASR enrichment validated** (spike, `docs/spike-asr/METHODOLOGY.md`): mlx-whisper `large-v3-turbo` transcribes French sermons ~6× real-time locally; LLM topics/summary are confirm-don't-type quality. **Title → scripture; transcript → topics/summary/series/search.** Speaker inference needs a default rule, not ASR.

## How to run the pipeline

```bash
python3 pipeline/build.py             # runs the whole pipeline in order (recommended)

# order (build.py does this): parse → match → fold → cluster
python3 pipeline/parse_catalog.py     # SoundCloud titles -> data/catalog/catalog.json (239)
python3 pipeline/match_youtube.py     # link YT videos; write youtube_orphans.json
python3 pipeline/fold_orphans.py      # fold orphans -> unified catalog (~467, canonical schema)
python3 pipeline/cluster_series.py    # series over the union + write series.json + catalog.csv
```
Re-pulling inventories needs a recent yt-dlp (≥2026.x for YouTube's layout); the TSVs use a **literal `\t`** separator (yt-dlp didn't expand the escape) — the loaders handle this with `line.replace("\\t","\t")`.

**Enrichment pipeline** (per-sermon, M5):
```bash
python3 -m unittest discover -s tests        # 20 tests, offline, pure stdlib — no venv needed

# one-time setup (everything project-local & gitignored):
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
cp .env.example .env        # then put your ANTHROPIC_API_KEY in .env

# real run (uses the .venv python so anthropic/yt-dlp/mlx-whisper are importable; auto-loads .env):
./.venv/bin/python pipeline/build_entry.py --soundcloud-url <url> --raw-title "<title>"
```
Everything the pipeline needs lives **inside the project** (never `/tmp`):
- **`.venv/`** (gitignored) — yt-dlp ≥ 2026.x, mlx-whisper, anthropic (see `requirements.txt`). `transcribe.py` defaults to `.venv/bin/*` (override via `SERMO_YTDLP` / `SERMO_MLX_WHISPER`).
- **`cache/`** (gitignored) — downloaded audio + scratch; audio is deleted after transcription.
- **`.env`** (gitignored; template `.env.example`) holds `ANTHROPIC_API_KEY` for the enrich step (model `claude-sonnet-4-6`, **~$0.06/sermon measured** — full transcript ≈ 13–16k input tok + 1.5k out; Haiku 4.5 ≈ $0.02/sermon) — the CLI auto-loads it. Without a key the deterministic steps still run; inject your own `enrich` fn. *(`.venv` ≈ node_modules ← `requirements.txt`; `.env` ≈ Node's `.env` ← `.env.example`.)*
- The only thing *outside* the project is the Whisper model (~1.6 GB) in the standard `~/.cache/huggingface` shared ML cache — conventional and persistent, not scratch.
- Nothing critical is unrecoverable: the pipeline is committed, audio re-downloadable, transcripts regenerable.

## Current status & next steps

**Done:** planning/specs · M1 catalog · M1b series · M2 YT↔SC matching · M2b duration dedup (union 467) · M3 ASR+LLM spike (PASS) · M3b n=8 sample · M4 fold→unified 467 · **M5 enrichment pipeline `build_entry` + 20 tests** · git + GitHub remote.

Catalog is the **unified 467-record union** (239 SoundCloud + 228 YouTube), one canonical schema with `source` + `media`, 25 series. The per-sermon pipeline exists; it has NOT yet been run across the catalog.

**Open / next (pick up here):**
1. **POC DONE** (2026-06-14): real pipeline ran on the 8 sample sermons (full audio). **8 canonical transcripts now in `data/catalog/transcripts/`**; merged entries + Claude enrichment in `docs/spike-asr/poc_entries.json`; **elder-facing `docs/spike-asr/POC.{md,pdf}`** (5 pp). Scripture/kind parsed correctly incl. cross-chapter + the `Leçon`→teaching. **Enrichment is REAL**: ran `enrich.py` (Claude `sonnet-4-6`) on the 8 full transcripts (**$0.51 total ⇒ ~$0.06/sermon measured**; the earlier "~16¢/~$0.02" figure was Haiku pricing, not the Sonnet path actually run) — first execution of that path, validated; full-text summaries + **body-cited `scripture_refs` (3–15/sermon)**, far richer than the earlier slice version.
2. **Full ASR enrichment pass** — run `build_entry` across the catalog (~15× real-time ⇒ ~15 h for 239 SC sermons, a few overnight runs) → write topics/summary/transcript back to `catalog.json`. Needs `ANTHROPIC_API_KEY` for the enrich step: **~$0.06/sermon on Sonnet 4.6 ⇒ ~$12 for the 239 SC / ~$23 for the full 467** (Haiku 4.5 ≈ ⅓ that, but see decision #40 — Sonnet chosen for FR/theological precision). Add a **default-speaker rule** for untagged sermons.
3. **JSON Schema + WP import** — freeze the canonical record contract; design the WordPress CPT/ACF import → first public deliverable (website sermon library).
- *(Optional: also fold the 102 Live `Service` records in — currently only the 228 Videos-tab orphans are folded.)*

**Still-open design questions:** SoundCloud trim (only the sermon, or intro/offering too?), canonical hosting location, dedup edge cases (multi-part, re-uploads). See docs/SERMOTHEQUE.md §8.

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
