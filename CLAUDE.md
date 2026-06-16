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
| `pipeline/scripture.py` | Shared parsing primitives (OSIS book map, scripture/speaker/series parsing). Imported by the others. |
| `pipeline/parse_catalog.py` · `match_youtube.py` · `fold_orphans.py` · `cluster_series.py` · `enrichment_store.py` | **Catalog-build** pipeline (batch, pure-stdlib). `build.py` runs them in order, ending with the enrichment **writeback** (#44). |
| `pipeline/build_entry.py` | ★ **Single entry point**: `build_entry(source, *, transcribe, enrich)` — one YT/SC source → one canonical entry. |
| `pipeline/run_enrichment.py` | **Production runner** for the catalog-wide pass: resumable, logfile, live cost; `save_entry` per sermon → store + writeback (#44/#45). |
| `pipeline/transcribe.py` · `enrich.py` | The two **injected** external steps: mlx-whisper adapter (+ `clean_transcript`) and Claude-API adapter. |
| `tests/` | Stdlib `unittest` suite (offline). Run: `python3 -m unittest discover -s tests`. |
| `tools/md_to_pdf.py` | Markdown → PDF via headless Chrome (used for SYNTHESE / spike PDFs). |
| `docs/research/` | **Historical evidence** (not living docs): the M3 ASR spike (`METHODOLOGY.md`, `RESULTS.md`/`.pdf`) + the M5b POC (`POC.md`/`.pdf`, `poc_entries.json`) + `spike-transcripts/` (the original slices the spike ran on). |
| `data/raw/*.tsv` | Raw inventories pulled via `yt-dlp`. `data/catalog/` = canonical dataset (`catalog.json`/`.csv`, `series.json`, `youtube_orphans.json`, `enrichment.json` [id-keyed enrichment, #44], `transcripts/`). |
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
```
Everything the pipeline needs lives **inside the project** (never `/tmp`):
- **`.venv/`** (gitignored) — yt-dlp ≥ 2026.x, mlx-whisper, anthropic (see `requirements.txt`). `transcribe.py` defaults to `.venv/bin/*` (override via `SERMO_YTDLP` / `SERMO_MLX_WHISPER`).
- **`cache/`** (gitignored) — downloaded audio + scratch; audio is deleted after transcription.
- **`.env`** (gitignored; template `.env.example`) holds `ANTHROPIC_API_KEY` for the enrich step (model `claude-sonnet-4-6`, **~$0.06/sermon measured** — full transcript ≈ 13–16k input tok + 1.5k out; Haiku 4.5 ≈ $0.02/sermon) — the CLI auto-loads it. Without a key the deterministic steps still run; inject your own `enrich` fn. *(`.venv` ≈ node_modules ← `requirements.txt`; `.env` ≈ Node's `.env` ← `.env.example`.)*
- The only thing *outside* the project is the Whisper model (~1.6 GB) in the standard `~/.cache/huggingface` shared ML cache — conventional and persistent, not scratch.
- Nothing critical is unrecoverable: the pipeline is committed, audio re-downloadable, transcripts regenerable.

## Current status & next steps

**Done:** planning/specs · M1 catalog · M1b series · M2 YT↔SC matching · M2b duration dedup (union 467) · M3 ASR+LLM spike (PASS) · M3b n=8 sample · M4 fold→unified 467 · **M5 enrichment pipeline `build_entry`** · M5b POC (8 real sermons) · M5c cost + Haiku-vs-Sonnet bake-off · M5d timestamp capture · M5e docs restructure · **M5f pipeline hardening (cap 120k, YT date, live tracking + cost, txt+vtt default) + first real YT run** · **M5h matcher hardening (false positives fixed; union 467→517)** · **M5i enrichment writeback (#44)** · **M5j production runner + default-speaker rule (#45)** · 34 tests · git + GitHub remote.

Catalog is the **unified union of 517 records** (239 SoundCloud + 278 YouTube-only), one canonical schema with `source` + `media`, 26 series. The per-sermon pipeline is **validated end-to-end** (hardened, re-run on the 8 samples + a real YouTube sermon). **Enrichment now persists across rebuilds** via an id-keyed store (`data/catalog/enrichment.json`) + writeback in `build.py` (#44) — **9 rows enriched so far** (the 8 samples + `yt-IqNmh_XGULE`). The full catalog-wide enrichment pass has NOT yet run.

**Open / next (pick up here):**
1. **POC DONE** (2026-06-14): real pipeline ran on the 8 sample sermons (full audio). **8 canonical transcripts now in `data/catalog/transcripts/`**; merged entries + Claude enrichment in `docs/research/poc_entries.json`; **elder-facing `docs/research/POC.{md,pdf}`** (5 pp). Scripture/kind parsed correctly incl. cross-chapter + the `Leçon`→teaching. **Enrichment is REAL**: ran `enrich.py` (Claude `sonnet-4-6`) on the 8 full transcripts (**$0.51 total ⇒ ~$0.06/sermon measured**; the earlier "~16¢/~$0.02" figure was Haiku pricing, not the Sonnet path actually run) — first execution of that path, validated; full-text summaries + **body-cited `scripture_refs` (3–15/sermon)**, far richer than the earlier slice version.
2. **MATCHER HARDENED (DONE, decision #43)** — duration now only corroborates; union re-derived to **517** with 0 false positives. ✓
3. **Re-run the sample-8 with the hardened pipeline** (in progress) — full confidence before the catalog-wide pass.
4. **ENRICHMENT WRITEBACK DONE (decision #44)** — id-keyed `data/catalog/enrichment.json` + `writeback()` as the final `build.py` step; survives rebuilds. ✓
5. **RUN the full ASR enrichment pass** — the runner is built (`pipeline/run_enrichment.py`, resumable + logfile + cost) and the default-speaker rule is in (#45). Run: `./.venv/bin/python pipeline/run_enrichment.py --source soundcloud`. **Cost with the rich schema (description/invitation/summary/key_points/chapters/topics/references/key_quotes/questions/scripture): ~$0.078/sermon on Sonnet ⇒ ~$19 for the 239 SC / ~$40 for the full 517** (Haiku ≈ ⅓). *Exceeds the current ~$22 credit for the full union — top up, or run the SC spine on Sonnet (~$19) and the YT-only bulk on Haiku.* Needs `ANTHROPIC_API_KEY`. *(Text-derived enrichment is re-runnable from committed transcripts without re-ASR; only audio-derived data — transcript/timestamps/voiceprint — is truly one-shot.)*
6. **JSON Schema + WP import** — freeze the canonical record contract; design the WordPress CPT/ACF import → first public deliverable (website sermon library).
- *(Optional: also fold the 102 Live `Service` records in — currently only the Videos-tab orphans are folded.)*

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
