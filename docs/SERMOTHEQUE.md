# Sermothèque EBN — Sermon & Service System of Record

**Status:** Draft v1 (for grilling)
**Last updated:** 2026-06-14
**Owner:** kevy@merca.team
**Relationship to other docs:** This is the **parent project**. The app suite ([PRD.md](PRD.md)) and the website sermon library are *downstream consumers* of this system.

---

## 1. Mission

Build the church's durable **system of record for its preaching** — a clean, rich, portable catalog of every sermon and service, plus the pipeline that keeps it fed.

**Principle:** *The catalog is the asset; every app, site, and platform is a replaceable window onto it.* YouTube, SoundCloud, the website, the future mobile/TV apps — all are rendering surfaces. The content compounds in value for decades; the shells come and go. So we build the content system well, once, and let it outlive everything downstream.

## 2. Architecture — three layers

```
┌─ AUTHORING (write)  — replaceable input surfaces
│   • WordPress admin   (humans: media team, elders — friendly guided forms)
│   • the pipeline      (machines: yt-dlp · ASR · LLM · thumbnail render)
│        │ both write Sermon/Service records
│        ▼
├─ CANONICAL (own)  ★ THE PROJECT ★  — the durable asset
│   • clean, app-agnostic, VERSIONED dataset (structured records + media refs)
│   • a stable Catalog API + full-text / transcript search index
│   • single source of truth; portable; survives WordPress being thrown away
│        │ everything reads from here
│        ▼
└─ CONSUMPTION (read)  — replaceable output surfaces
    • WP website sermon library   • mobile + TV apps   • YouTube thumbnail pusher
```

**WordPress authors, but does not own.** Volunteers keep the friendly admin; every change syncs out to the canonical dataset, which is the real source of truth.

### Canonical storage (recommended)
- **Serving + search:** a real datastore (lightweight DB or prebuilt static JSON index) exposes the **Catalog API** that shells read.
- **Durable archive of record:** a **version-controlled flat-file export** (one JSON record per sermon/service, committed to git) — diff-able, portable, human-readable, survives any platform. Regenerated on every change.
- Church-scale volume (hundreds → low thousands) means static JSON + a prebuilt search index is plenty and near-zero ops; a server DB (Meilisearch/Typesense/Postgres) can replace the serving layer later if scale demands, without touching the canonical archive.

## 3. Canonical data schema (the heart — grill this)

First-class, related entities (not flat tags):

### `Sermon` — the core preaching unit
| Field | Type | Notes |
|---|---|---|
| `id` | slug + UUID | **stable, permanent** — the cross-shell contract (e.g. `2026-03-15-galates-6-14`) |
| `title` | text | |
| `language` | enum | `fr` (default) · `en` · `pt`; conference sermons exist in EN |
| `date` | date | preached date |
| `speaker_id` | → Speaker | |
| `series_id` | → Series (nullable) | |
| `series_part` | int (nullable) | "Partie V" → 5 |
| `primary_scripture` | ScriptureRef | the passage preached |
| `scripture_refs[]` | ScriptureRef[] | other passages cited (from transcript) |
| `topics[]` | → Topic[] | curated vocabulary |
| `summary` | text | AI-generated, human-confirmed |
| `transcript_ref` · `captions_ref` · `segments_ref` | files | ASR output (labeled "auto-generated"), named **`<entry-id>.<ext>`** — `<id>.txt` (plain) + `<id>.vtt` (segment timing) + `<id>.json` (word timing + confidence), sharing a stem with the catalog `id`. Translated subtitles later use a language infix: `<id>.en.vtt`, `<id>.pt.vtt`. See the naming convention in #42. |
| `media` | object | `{ soundcloud_url, youtube_id, audio_duration }` |
| `thumbnail_ref` | image | from the pipeline |
| `translation_of` | → Sermon (nullable) | links EN/FR versions of the same conference sermon |
| `provenance` | object | per-field: `ai_suggested` vs `human_confirmed` + source + confidence |
| `status` | enum | `draft` · `enriching` · `needs_review` · `published` |
| `created/updated/version` | meta | audit trail (append-only history) |

### `Service` — full Sunday service (light)
| Field | Type | Notes |
|---|---|---|
| `id` | slug + UUID | |
| `date` | date | |
| `title` | text | "Culte Dimanche DD/MM" |
| `youtube_id` | text | full-service / past live stream |
| `duration` | int | ~2 h |
| `preacher_id` | → Speaker (nullable) | |
| `sermon_id` | → Sermon (nullable) | the sermon cut from this service, if identified |
| `streamed` | bool/derived | feeds the app's Live/archive |

### Supporting entities
- **`Series`** — `id`, `name`, `type` (`sermon-series` \| `conference`), `description`, `date_range`, derived `sermon_count`.
- **`Speaker`** — `id`, `name`, `role` (`pastor`/`elder`/`guest`), `is_guest`, optional `bio`, `photo`.
- **`Topic`** — `id`, `label` (FR + EN/PT translations of the *label* only), `description`, derived `sermon_count`. Curated vocabulary, AI-bootstrapped from the corpus.
- **`ScriptureRef`** — structured value object: `book` (canonical name), `chapter`, `verse_start`, `verse_end`. Enables **browse-by-book** ("all sermons in Romans"). *(Open: adopt a standard like OSIS for book IDs.)*

### Provenance & "confirm-don't-type"
Every auto-extracted field carries provenance (`ai_suggested` / `human_confirmed`, source, confidence). This powers the **completeness dashboard** (§5) — the system always knows what still needs a human eye.

## 4. The pipeline (per sermon — new + backfill)

1. **Ingest + parse title** — SoundCloud track (spine) + matched YouTube video. Parse the structured SC title `Title | Scripture | (Pr. Speaker)` → pre-fill title/scripture/speaker/series (~74% yield, free).
2. **Transcribe** — ASR (Whisper large-v3-class) on the **clean SoundCloud audio** → transcript + `.vtt`. Clean source = no hymn/offering pollution.
3. **AI enrich** — LLM reads the transcript → proposes `topics` (from vocabulary), `summary`, confirms/augments scripture refs.
4. **Human pass** — one screen: confirm AI suggestions **and** pick the thumbnail frame (top 3). Confirm-don't-type.
5. **Render thumbnail** — branded overlay over chosen frame → 1280×720.
6. **Publish + export** — write record; regenerate canonical export + search index; push thumbnail to YouTube (Data API); fire notification.

## 5. Management surface

- **Authoring:** locked-down WP admin guided form (publish new) — for the media team / elders.
- **Curation console (the "management solution"):** a catalog-wide view with a **completeness dashboard** — surfaces what's missing or unconfirmed: no scripture, unconfirmed AI fields, unmatched YT↔SC, no thumbnail, no transcript, orphan series. Bulk edit; manage Series / Speakers / Topics. Recommended to live as custom pages **inside WP admin** (one tool, same records), not a second app.
- **Roles:** Publisher (media team/elders) + Admin (pastor + technical owner) — per [PRD.md](PRD.md) §8.

## 6. Backfill plan (measured inventory — raw files in `data/raw/`)

| Source | Count | Role |
|---|---|---|
| SoundCloud tracks | **239** | **spine** of the sermon catalog (cleanest titles) |
| YouTube Videos | **300** | cut-sermon videos — matched in by title/date |
| YouTube Live | **102** | `Service` records (light) |

Sequence:
1. **Instant first-pass catalog** — parse the 239 SC titles → structured Sermon records (title/scripture/speaker/series). A usable catalog *immediately*, no ASR needed.
2. **Match YT → SC** — fuzzy title + date match the 300 videos onto Sermons; attach `youtube_id`; report orphans (likely EN conference videos with no SC counterpart).
3. **Import Services** — the 102 streams → `Service` records.
4. **Enrich** — batch ASR + LLM over the corpus → transcripts, topics, summaries, search index.
5. **Human confirmation sweep** — driven by the completeness dashboard.
6. **Thumbnails** — pipeline over the catalog.

## 7. Roadmap

- **M1 — Foundations & instant catalog:** canonical schema + repo + export format; WP authoring model; first-pass backfill from SC titles (a real catalog on day one).
- **M2 — Matching & console:** YT↔SC matching + services import; completeness dashboard.
- **M3 — Enrichment & search:** ASR + LLM + full-text/transcript search.
- **M4 — Thumbnails:** branded thumbnail pipeline + YouTube push.
- **M5 — First public window:** website sermon-library section reading the Catalog API.
- **Later — Apps:** mobile + TV consume the same Catalog API ([PRD.md](PRD.md)).

## 7b. Build log

> Append a dated entry here whenever you complete a step, and follow the **Maintenance protocol** in `CLAUDE.md` (sync README/CLAUDE.md status + roadmap, commit, push).

**M1 first-pass catalog — DONE (2026-06-13).** `pipeline/parse_catalog.py` parses the 239 SoundCloud titles → `data/catalog/catalog.json` + `.csv`. Coverage (titles only, no ASR):
- Scripture (OSIS): **196/239 (82%)**, 80% high-confidence, across **24 books**.
- Clean title: 87% · Speaker: 26 named (mostly the regular pastor is untagged) · Series part: 34 · English: 0 (SoundCloud is FR-only).
- Distribution reveals systematic expository series: **Galates 72, Hébreux 28, Genèse 16, Jacques 14, Ézéchiel 11**.
- Known limitations carried to enrichment: the 43 refless items (intros/Q&A/topical), speaker inference for the regular preacher, multi-range verses approximated as a span.

**M1b series clustering — DONE (2026-06-13).** `pipeline/cluster_series.py` → `data/catalog/series.json` + enriches catalog. **22 series, 81% of sermons placed**, ordered by chapter:verse. Expository: Épître aux Galates (69), aux Hébreux (28), de Jacques (14), Genèse (13), Ézéchiel (11)… Thematic: Joie chrétienne, Noël le plus glorieux des mystères, Fruit de l'Esprit… Pipeline order: `pipeline/build.py` runs parse → cluster → match.

**Git — DONE (2026-06-13).** Repo initialized (branch `main`); the canonical dataset is now version-controlled per the durability decision. Initial commit `e2d3218`. Pushed to private GitHub repo `KevyMbappe/sermotheque-ebn`.

**M2 YouTube↔SoundCloud matching — DONE (2026-06-13).** `pipeline/match_youtube.py` (scripture-anchored + language-aware) → enriches catalog + `data/catalog/youtube_orphans.json`. **Finding: YouTube's Videos tab is NOT a mirror of SoundCloud** — only **17** confident same-language overlaps. YT is dominated by **conference content (48, CBN Paris / international guests)**, **English** material, and ~215 French videos not title-matchable to SC. The real catalog is the **UNION**, not the 239 SC spine. *Decision #37 (below).*

**M2b duration fingerprint — DONE (2026-06-13).** Re-pulled SoundCloud **durations + dates** for all **239/239** tracks (fast extraction rate-limits after ~146; a throttled `--sleep-requests 1.5` pass completed the rest). Data now `id⇥duration⇥upload_date⇥title`. Calibrated on known-same pairs: **YouTube runs a near-constant +51 s longer than SoundCloud** (range +26…+63 — an intro/outro card) — a sermon's length is effectively a fingerprint. Added an offset-corrected duration signal to the matcher. **Final result (full coverage):** same-language matches **17 → 61**, translations **2 → 11**, orphans **281 → 228**. **Union = 467 distinct sermons** (239 SC + 228 YT-only: conference ~45, English ~21, SC-absent French ~162). No caveat — duration coverage is complete.

**M3 ASR + LLM enrichment spike — DONE (2026-06-13).** Transcribed one sermon (mlx-whisper `large-v3-turbo`, ~6× real-time, local/free) and enriched it. **PASS** — excellent French ASR (cosmetic artifacts only), accurate zero-hallucination topics/summary, and it *recovered series context the title lacked* (Confession de foi 1689, ch. 8). Refined division of labor: **title → primary scripture; transcript → topics/summary/series/search**. Speaker inference is the weak spot (use a default rule, not ASR). Full write-up: `docs/research/METHODOLOGY.md`.

**M3b ASR bigger sample (n=8, 2023→2026) — DONE (2026-06-13).** 8 sermons across the archive (incl. oldest + multiple speakers): **zero failures, uniformly high quality across all eras**. Errors are **systematic** (foi→fois, le→les, Dieu→dieux for the regular pastor) → cheap regex post-clean. Different (native-FR) speakers transcribe even cleaner (artifact = weak speaker fingerprint). **Speed (measured on a full sermon):** ~15× real-time ⇒ 239 SC sermons ≈ **~15 h local compute** (a couple of overnight runs). Verdict: green-light the full pass, with a regex normalization step + a default-speaker rule.

**M4 fold orphans → unified catalog — DONE (2026-06-13).** `pipeline/fold_orphans.py` merges the 239 SoundCloud records + 228 YouTube orphans into **one catalog of 467 records** with a uniform canonical schema (`id`, `source`, `media`, enrichment placeholders). Pipeline order is now **parse → match → fold → cluster** (`build.py`); series clustering runs over the union → **25 series** (new ones surfaced from YT/conference content). `catalog.csv` is now the flattened 467-row export written by the final step. *(Not yet folded: the 102 Live `Service` records — a separate light type.)*

**M5 enrichment pipeline — built (2026-06-13).** `pipeline/{transcribe,enrich,build_entry}.py` — single entry point `build_entry(source, *, transcribe, enrich)` (YT/SC ids/URLs → one canonical catalog entry). Transcribe + enrich are injected (real adapters: mlx-whisper, Claude API). Conservative ASR cleanup (`clean_transcript`). Tests: `tests/` (stdlib unittest) — **20 tests, offline/deterministic**, covering parsing edge cases, cleanup (with negatives), and end-to-end assembly. Storage per #38 (transcripts→git, audio→gitignored `cache/`).

**M5b POC — DONE (2026-06-14).** Ran the real pipeline on the 8 sample sermons (full audio, 7–11.5k words each): scripture/kind parsed correctly (incl. cross-chapter `Gen.1.1-Gen.2.3`, `Leçon`→teaching). **Real enrichment ran** (`enrich.py` → Claude `sonnet-4-6`, ~16¢, first execution of that path — validated): full-text summaries + body-cited `scripture_refs` (3–15/sermon, vs ~0 in the slice spike) + series context. 8 transcripts committed to `data/catalog/transcripts/`; demo entries `docs/research/poc_entries.json`; elder-facing `docs/research/POC.{md,pdf}` (5 pp). Environment is now project-local (`.venv` + `requirements.txt`, `cache/`, `.env`/`.env.example`) — no `/tmp`.

**M5c cost reconciliation + model bake-off — DONE (2026-06-14).** The 8-sermon POC enrichment cost **$0.51 ⇒ ~$0.06/sermon on Sonnet 4.6**, *3× the "~$0.02" carried in the docs (that was Haiku pricing) — corrected everywhere.* Ran a **Haiku 4.5 vs Sonnet 4.6** head-to-head on one rich sermon (`sc-2338530545`): both excellent and well-cited; **Sonnet kept as default** — it names heresies precisely and writes clean French where Haiku slipped typos/anglicisms. Full bake-off + pricing reference: [`docs/ENRICHMENT-MODEL.md`](ENRICHMENT-MODEL.md); reasoning in decision #40. Full-pass budget: **~$12 (239 SC) / ~$23 (467 union)**. Also locked **decision #41 (ASR backend pluggable — mlx now, cloud Whisper API on the church's Windows machines in production)**.

**M5d timestamp capture — DONE (2026-06-14, decision #42).** Extended the ASR step to emit **segment + word-level timestamps** in the same pass (mlx-whisper `--output-format all --word-timestamps True`, free). `transcribe_fn` now returns `{text, vtt, segments, language}`; `build_entry` persists `<id>.txt` + `<id>.vtt` (subtitle-ready) + `<id>.json` (word timing + per-segment confidence). Back-compatible — fakes returning a plain string still work. Tests: **20 → 22** (added the rich-result persistence path + the string fallback), all green offline. Unlocks EN/PT subtitles, deep-linking, search-to-moment, and confidence-flagged review without ever re-running ASR. **Transcript naming convention formalized** (see #42): canonical files are `<entry-id>[.<lang>].<ext>`, flat, keyed to the catalog `id`. *(Note: the 8 committed POC transcripts are still text-only `.txt` — they predate this change; they'll gain `.vtt`/`.json` when the full pass runs, since regenerating 8 means a fresh download+ASR. Git-weight: VTT ≈ 2× the `.txt`; word-level JSON is heavier (~5–10×) — committed by default per "capture once", revisit if the union's transcripts dir grows past a comfortable size.)*

**M5l enrichment schema expansion + audio fingerprint validated — DONE (2026-06-16).** Audio voiceprints (Resemblyzer, torch already present) tested on 20 labeled sermons: **8/8 on title-confirmed speakers** (Stephan 6/6, Nathanaël 2/2 — text got Nathanaël 0/2), and it **caught a real default-rule mislabel** — the Ézéchiel sermon `sc-1900264623` (auto-credited David) is **Stephan**, human-confirmed. So Tier B (audio) is the substrate for the speaker store; text Tier A stays a weak flag. Enrichment schema expanded to the full WP-facing set (decision #46 fields): **description, invitation** (warm-sober blogger blurb), **summary, key_points, chapters** (title + verbatim anchor → VTT timestamp), **topics, doctrines** (validated distinct from topics), **references, key_quotes** (verbatim → VTT timestamp), **questions**, scripture. `build_entry._vtt_locate` anchors quotes/chapters to real times. **`speaker_provenance`** now on every record + in the CSV (428 default-rule / 45 title / 44 blank) — the rung for `audio-fingerprint`/`human` lands when the speaker store is wired. Live validation caught + fixed two run-killer bugs (prompt brace, `max_tokens` truncation). **Cost with the rich schema: ~$0.078/sermon** (Sonnet) ⇒ ~$19/239 SC, ~$40/517. Translation-friendly: French source now, controlled vocabs translate once, prose later — text-derived fields re-runnable from committed transcripts (no re-ASR). Tests 34 → 50.

**M5j production runner + default-speaker rule — DONE (2026-06-16, decision #45).** `pipeline/run_enrichment.py`: the catalog-wide pass over `build_entry` — **resumable** (skips ids already in the store, so a kill at #300 resumes there), **logfile** (`logs/enrichment.log`, per-sermon id/time/tokens/cost + running total), live cost, `--source`/`--ids`/`--limit`/`--model`/`--segments`, and `save_entry` per sermon + a final writeback. Resolves URLs (YT from id; SC via a cached channel map). Smoke-tested on the no-op/resume path. **Default-speaker rule (#45):** untagged sermons → David Pelosi (the regular preacher); conferences/English left unattributed; attribution went 45 → 473/517. Tests 28 → 34. **The full pass is now fully unblocked** — `./.venv/bin/python pipeline/run_enrichment.py --source soundcloud` runs the 239 SC spine (~16 h, ~$15).

**M5i enrichment writeback layer — DONE (2026-06-16, decision #44).** `pipeline/enrichment_store.py`: id-keyed store `data/catalog/enrichment.json` + `writeback()` wired as the final step of `build.py`. Enrichment now lives outside the structurally-regenerated catalog and is re-merged after every rebuild — proven by rebuilding from raw and seeing the 9 seeded entries (8 samples + `yt-IqNmh_XGULE`) come back enriched. Unblocks the full pass (the runner calls `save_entry` per sermon; `build.py` re-applies). Tests 25 → 28.

**M5f pipeline hardening + first real YT run — DONE (2026-06-14).** Ran the full per-sermon pipeline end-to-end on a sermon *outside* the sample-8 — YouTube `IqNmh_XGULE` (*Prier selon le cœur de Dieu IV | Psaume 40*, 59 min): parse/scripture/series-part all correct, 8.4k-word transcript, rich enrichment. Fixes applied off the back of it: (1) **enrichment input cap 48k → 120k chars** — the 48k cap had silently truncated this sermon's conclusion (re-enriching the full text recovered refs *Psaume 51* and *Hébreux 5:7-9*); (2) **YouTube `upload_date` now captured** into the entry (`build_entry` date falls back to `source.upload_date`; the CLI probes it via yt-dlp) — fixes `date: null`; (3) **live progress tracking + cost line** — Tier 0 (yt-dlp/whisper progress streamed to stderr) + Tier 1 (`on_progress(phase)` callback + `on_usage` → `cost_of(model, in, out)` from the real pricing table in `enrich.py`); stdout stays clean JSON; (4) **word-level `.json` now opt-in** (`--segments`), default keeps `.txt`+`.vtt` (decision #42 git-weight). Measured enrich cost on this sermon: **$0.058** (17.4k in + 382 out, Sonnet 4.6). Tests **22 → 25**. Still open: default-speaker rule (`speaker: null`), and full-pass essentials (logfile + resumability).

**M5g catalog correction → M5h matcher hardening — DONE (2026-06-14, decisions #43/#44).** The real run exposed a **false-positive YT↔SC match** (`IqNmh_XGULE` Psaume 40 wrongly attached to the Genèse SC sermon via a 5-second duration collision, 0.656). An audit found the whole **0.6–0.7 band (36 matches) was duration-only and mostly spurious**. Fixed properly in `match_youtube.py` — **duration now only corroborates; title or scripture must carry the match** — and rebuilt: **overlaps 61→18, translations 11→4, orphans 228→278, union 467→517**, with 0 false positives remaining and 0 real matches wrongly demoted (the one-off 468 hand-patch is superseded). The rebuild also surfaced **#44**: enrichment written into `catalog.json` is wiped by a rebuild → the full pass needs a separate id-keyed enrichment store + writeback step (build before scaling).

**M5e docs restructure — DONE (2026-06-14).** `docs/spike-asr/` was a misnomer — it held a live reference doc, an elder-facing POC, *and* genuine spike evidence under one "throwaway" name. Reorganized: **promoted `ENRICHMENT-MODEL.md` → `docs/`** (it's a current reference, consulted before the full pass), **renamed `spike-asr/` → `research/`** (honest: holds the M3 spike + the M5b POC as the historical record), renamed its `transcripts/` → `spike-transcripts/`, and **dropped one duplicate** (`01_…_FULL.txt` was byte-for-byte the canonical `sc-2338530545.txt`). The 8 original spike slices are kept as evidence (they're the literal inputs `METHODOLOGY`/`RESULTS` describe). All ~7 cross-references in `CLAUDE.md`/`README.md`/this spec updated; `git mv` preserved history.

## 8. Resolved design decisions (grilled 2026-06-13)
- **Scripture:** canonical **OSIS** book IDs (e.g. `Rom.8.1-8.4`) + a FR/EN parser; display localized, query canonical. Powers browse-by-book.
- **EN/FR pairing:** **independent** Sermon records linked by `translation_of` (each keeps its own media/transcript/thumbnail).
- **Versioning/audit:** **git history of the flat-file export** is the audit trail; live store is last-writer-wins. Zero extra infra.
- **Search:** **prebuilt static index** (FlexSearch/lunr/Pagefind) regenerated on export; near-zero ops, no server. Upgrade to a managed search server later only if scale demands.
- **Topic labels:** translated **FR + EN + PT** (bounded ~30–60 list); matches the trilingual UI.
- **YT↔SC matching (backfill):** **fuzzy title + date window**; high-confidence auto-link, low-confidence to the completeness dashboard; orphans (EN-only videos) flagged, not forced.

### Decision (added)
- **#38 (2026-06-13) — Storage split:** **transcripts are committed to git** (`data/catalog/transcripts/*.txt`, ~25 MB total — text, canonical, diffable). **Audio is never committed** — downloaded to a gitignored `cache/`, deleted after transcription; it's regenerable via `yt-dlp` and the church's SoundCloud/YouTube are the durable audio archive. Media artifacts (thumbnails) later go to object storage / WP media, referenced by URL — not git.
- **#39 (2026-06-13) — Pipeline shape:** single entry point `build_entry(source, *, transcribe, enrich)` composing parse → transcribe → enrich → assemble; the two external steps are **injected** (real = mlx-whisper + Claude API; tests inject fakes) → fast offline deterministic tests + one global integration test. Production enricher = Claude `claude-sonnet-4-6`, structured JSON output, **~$0.06/sermon measured** (needs `ANTHROPIC_API_KEY`). *(Cost & model choice refined in #40.)*
- **#40 (2026-06-14) — Enrichment cost (measured) + model choice:** The real POC run cost **$0.51 for 8 full sermons ⇒ ~$0.06/sermon on `claude-sonnet-4-6`** — *3× the "~$0.02" figure carried in earlier docs, which was actually Haiku 4.5 pricing, never reconciled against a Sonnet run. Corrected throughout.* A **Haiku 4.5 vs Sonnet 4.6 bake-off on one rich sermon** (incarnation/Christology, `sc-2338530545`): both produced excellent, faithful, well-cited output (~identical scripture refs); **Sonnet wins on two material points for FR/theological content** — it names heresies precisely (docétisme, nestorianisme, modalisme) where Haiku stays generic, and its French is clean where Haiku slipped anglicisms/typos ("essential", "necessaires") and a malformed series label. Measured per-sermon: **Haiku $0.018, Sonnet $0.053. Decision: keep Sonnet 4.6 as the default enricher** — at ~$12 for the 239 SC sermons / **~$23 for the full 467**, the quality margin (precision + clean French an elder will read) is worth ⅓-extra. Haiku stays a documented fallback for bulk/budget runs. Full-pass budget figures corrected in `CLAUDE.md`. **Full bake-off table, sample outputs, and the Claude pricing reference: [`docs/ENRICHMENT-MODEL.md`](ENRICHMENT-MODEL.md).**
- **#42 (2026-06-14) — Capture timestamps in the ASR pass (do it once):** The transcription step now emits **segment + word-level timestamps**, not just plain text — `transcribe_fn` returns `{text, vtt, segments, language}` and `build_entry` persists **`<id>.txt`** (plain, drives enrichment + search) + **`<id>.vtt`** (subtitle-ready segment timestamps) by default; the heavy **`<id>.json`** (word-level timing + per-segment confidence) is **opt-in** via `persist_segments=True` / the CLI `--segments` flag (see git-weight below). *Rationale:* ASR is the expensive step (download + ~15× real-time compute); emitting timestamps from that same pass via mlx-whisper `--output-format all --word-timestamps True` costs **nothing extra**, but re-deriving them later means re-running ASR on all 467. Capturing the maximum once unlocks, for free: **EN/PT subtitle generation** (translate the VTT cues, timing preserved), **audio-synced reading + deep-linking** ("jump to where he says X"), **search-to-moment**, and **confidence-flagged human review** (shaky stretches surface themselves). Conservative `clean_transcript` is applied to both text and VTT (its word-substitution rules never touch timestamp lines). Supersedes the text-only assumption in #38 — committed transcripts are now `.txt` + `.vtt`. **Git-weight (measured, decision validated 2026-06-14):** for a 59-min sermon, `.txt` 48 KB · `.vtt` 117 KB (~2.4×) · `.json` **1.5 MB (~30× the txt, ~220 KB gzipped)**. Word-level JSON is therefore **not committed** — kept opt-in (`--segments`) and regenerable from audio (ASR is local/free). Decision: **`.txt` + `.vtt` only for now** — segment-level timing covers subtitles/deep-linking, and even Grace-to-You doesn't ship word-level sync; revisit if a concrete use case (karaoke highlight, sub-second search-to-moment) justifies the weight.
  **Naming convention:** the filename is a *primary key, not a label* — **`<entry-id>[.<lang>].<ext>`**, flat in `data/catalog/transcripts/`. `<entry-id>` is the catalog `id` (`sc-<soundcloud_id>` / `yt-<youtube_id>`, from `build_entry`); all formats for one sermon share the stem (`sc-X.txt`/`.vtt`/`.json`), and the stem *is* the foreign key into `catalog.json`. Ids are stable; titles/dates/slugs drift and already live in the catalog, so they're kept out of filenames. Translated subtitles add a language infix (`sc-X.en.vtt`). *(Contrast: `docs/research/spike-transcripts/` keeps the spike's readable `NN_date_slug` names — right for a frozen 8-file evidence folder a human browses, wrong for a 467-row store tooling joins. Different masters, deliberately not unified.)*
- **#41 (2026-06-14) — ASR backend is pluggable (mlx-whisper now, cloud Whisper API in production):** Transcription is isolated behind `make_transcriber()` in `transcribe.py` and **injected** into `build_entry` (#39), so the ASR engine is a swappable adapter. **Now:** mlx-whisper `large-v3-turbo`, local on Apple Silicon, free, ~15× real-time — ideal for the one-time backfill on a Mac. **Production / new-sermon flow:** the church's machines are **Windows laptops** where mlx (Apple-only) won't run, so route to a **cloud Whisper-class API** (e.g. Groq `whisper-large-v3`, OpenAI, or a hosted endpoint) behind the same injected `transcribe_fn(source) -> {text, vtt, segments, language}` contract (see #42) — only `transcribe.py` changes, nothing downstream. The committed transcripts (#38) mean re-transcription is rarely needed; the backend choice is an operational detail, not a data-model one.
- **#43 (2026-06-14) — YT↔SC matcher produces false positives at the duration-collision boundary (found in the wild):** Validating the pipeline on YouTube video `IqNmh_XGULE` ("Prier selon le cœur de Dieu IV | **Psaume 40**") surfaced that it had been auto-matched as the `youtube_id` of an *unrelated* SoundCloud sermon `sc-2054926060` ("Image de Dieu | **Genèse 1:26-2:3**") at `youtube_match: 0.656`. Cause: the duration fingerprint — YT 3555 s vs SC 3550 s, a **5-second collision between two different ~59-min sermons** — plus a weak title signal cleared the auto-accept bar. This is the concrete instance of the "dedup edge case" risk. **Audit (2026-06-14):** of the 60 accepted matches, the ≥0.7 band (24) was clean but the **0.6–0.7 band (36) was duration-only** — 35/36 had near-zero title overlap, and all 3 that were scripture-checkable were false (incl. *Psaume 40 Parties IV **and** V* scattered onto unrelated Genèse/Colossiens sermons). **Fix (durable, in `match_youtube.py`):** the duration fingerprint now only *corroborates* — a match is accepted only when title agreement (`TITLE_STRONG = 0.62`) or exact scripture carries it; duration alone never does (`TITLE_WITH_DUR = 0.45`, `TITLE_WITH_SCR = 0.25`). Rebuilt via `build.py`: **same-language overlaps 61 → 18, translations 11 → 4, orphans 228 → 278, union 467 → 517** — ~43 "matches" were duration coincidences, and those YouTube videos now stand as their own entries. **Verified:** 0 book-mismatch false positives remain, and 0 orphans have a strong (≥0.6) title match to an SC sermon (nothing real was wrongly demoted). Supersedes the earlier one-off hand-patch (M5g, catalog 468).
- **#44 (2026-06-14) — Enrichment must be a separate layer, not stored in `catalog.json`:** `build.py` regenerates `catalog.json` from raw (parse→match→fold→cluster), so any enrichment written directly into it (topics/summary/`transcript_ref`/`scripture_refs`) is **wiped on the next rebuild** — observed when the #43 matcher rebuild erased the hand-added `yt-IqNmh_XGULE` enrichment (transcripts on disk survived; the catalog row went back to `topics:[]`). Therefore the full enrichment pass must write to a **separate id-keyed store** (e.g. `data/catalog/enrichment.json`) that a **writeback step merges into the rebuilt structural catalog**. Build this writeback *before* the catalog-wide enrichment pass, or every structural rebuild destroys ~$25 of work. (Transcripts under `data/catalog/transcripts/` are safe — they're keyed by id and not touched by `build.py`.) **RESOLVED (2026-06-16):** `pipeline/enrichment_store.py` implements the store (`data/catalog/enrichment.json`, id-keyed) + `writeback()`, now the final step of `build.py` (parse→match→fold→cluster→**writeback**). `save_entry(build_entry_result, model=…)` upserts per sermon during the pass; `apply()` is a pure merge of the enrichment fields (`topics, summary, primary_scripture, scripture_refs, series_hint, transcript_ref, captions_ref, segments_ref`) onto rows by id, leaving structure untouched. *(`speaker` is deliberately NOT stored — it's structural, set by the default-speaker rule #45 on each build.)* Seeded with the 9 entries enriched so far (8 samples + `yt-IqNmh_XGULE`); verified by a full `build.py` rebuild from raw — the 9 rows came back enriched (517 rows, 9 enriched). 3 offline tests cover the merge.
- **#37 (2026-06-13):** The catalog is the **UNION of SoundCloud + YouTube** (**467** distinct sermons), not the SC spine alone. SC = clean French expository audio (239); YouTube adds conference content (~45) + English versions + SC-absent French sermons. YT↔SC are largely *complementary*: with full duration coverage (239/239), duration-fingerprint matching (YT ≈ SC + 51 s) confirms **61** same-language overlaps + **11** translations; the remaining **228** YT videos are net-new.

- **#45 (2026-06-16) — Default-speaker rule + voice-ID deferred:** the regular, lusophone-accented preacher is **Pastor David Pelosi**; untagged sermons default to him. `resolve_speaker()` (scripture.py): an explicit speaker named in the title wins; **conference/English sermons are left unattributed** (typically named guests — don't mis-credit the pastor); everything else → David Pelosi. Applied in `parse_catalog`, `fold_orphans`, `build_entry`; **speaker is structural** (re-derived each build, not in the enrichment store). Rebuilt: attribution **45 → 473/517** (David Pelosi 449 + explicit guests like Stephan Kongo, Joël Beeke). *Caveat:* an untagged **guest** sermon gets mis-credited to the pastor — provenance is "default rule", correctable opportunistically. **Voice identification (diarization / speaker embeddings) considered and DEFERRED:** it needs heavy extra ML (pyannote/PyTorch + a voice-enrollment sample), runs on audio (re-downloadable, ~1–2× real-time), and the title default already covers the dominant case for free — revisit only if mis-attribution becomes a real problem, or for the bilingual EN-conference + live-translator case where two voices share one recording. **The goal is a binary gate, not 1:N identification:** "is this David?" → keep the default; "clearly not David" (rare) → leave blank for manual fill. **Now kept by default to support this:** the **uncleaned** ASR transcript as `<id>.raw.txt` (build_entry persists it; `raw_ref` in the store) — David's lusophone accent leaves systematic ASR artifacts there (the ones `clean_transcript` strips), so the raw text *vs* cleaned diff is itself an accent signal. (mlx-whisper gives words + timestamps + per-segment confidence, **not** voice/tone — a true voiceprint needs a separate speaker-embedding model on the audio; see the build-log assessment.)

- **#46 (2026-06-16, PLANNED) — "Sermon fingerprint" store for speaker attribution (curated, human-named, lightweight):** ~5 regular preachers (David + elders Stephan, Nathanaël, Loïc, Christian) cover 90%+; the rest are guests/trainees. Goal: a per-sermon **fingerprint**, recurring fingerprints → centroids a human **names**, new sermons snap to the nearest centroid → suggested speaker (or "unknown → leave blank"). At 500 sermons / 5 speakers this is **nearest-centroid classification** — no training, no neural nets, no infra.
  - **Store:** `data/catalog/fingerprints.json`, id-keyed: `{ features|embedding, assigned_speaker, method, confidence }`. Same id-keyed + writeback pattern as the enrichment store (#44); writeback sets `speaker` + **provenance ladder** `title > fingerprint-confirmed > fingerprint-suggested > default-rule (#45)` — never silently overwrite a human label.
  - **Two substrates.** *Tier A — text* (`pipeline/fingerprint.py`, pure stdlib): function-word stylometry (Burrows Δ) + **accent-artifact rate** (from the raw transcript — `clean_transcript` match count per 1k words; David's lusophone accent spikes it) + cadence (words/sec from the VTT) + vocab richness. Free, nails *David vs not-David*; **open question whether it separates the native-French elders from each other.** *Tier B — audio* (injected adapter, one small dep e.g. Resemblyzer): speaker-embedding verification, embed each sermon during the pass (audio already downloaded), cosine to per-speaker centroid. Reliable 5-way; **not** diarization (we have single-speaker recordings).
  - **Workflow (human-in-the-loop):** seed centroids from title-labeled sermons (ground truth) → classify the rest → a human confirms/names in batches → store + writeback. Bias the threshold toward *keeping the default* (only blank on confident not-David), since not-David is rare.
  - **Bonus:** the same fingerprints flag duplicates/re-uploads and can corroborate the YT↔SC matcher (#43).
  - **Test (M5k, DONE 2026-06-16):** transcribed 20 labeled sermons (David ×8, Stephan ×6, Nathanaël ×2, Loïc ×1, Christian ×1, Beeke ×1, Jonas ×1) and ran Tier-A leave-one-out. **Result: 12/16 — Stephan 6/6 ✓, David 6/8, Nathanaël 0/2 ✗.** Two clear findings: (1) **text stylometry works only with enough examples** — Stephan (6) separated perfectly, but the thin-data elder Nathanaël (2) failed entirely; the elders mostly have 1–2 labeled sermons, so centroids are starved. (2) **The accent-artifact feature is effectively dead** (`artifact/1k`≈0): `count_artifacts`'s 7 curated phrases are far too sparse to fingerprint an accent — the hypothesized cheap David signal did not materialize. **Conclusion: Tier A is a weak *review-flag* (~75–85%), not reliable elder attribution.** For a real "name the 5 preachers" store, **Tier B (audio embeddings) is the recommended substrate** — one enrollment clip per voice sidesteps the data-starvation that cripples text centroids, and voices separate where same-church text styles don't. Decision: keep Tier A only as an optional "looks-not-David → review" flag; build the fingerprint store on audio embeddings if/when speaker attribution is prioritized.

### Still open (lighter — resolve during build)
- **YT↔SC true overlap** — dedup the ~215 French YT orphans against SC needs a stronger signal than titles: re-pull `duration`+`upload_date` (both platforms) and match on those, or use embeddings/audio fingerprint.
- **Canonical hosting** — where the git export repo + static serving live (church-owned, per [PRD.md](PRD.md) §8 ownership model). Static index ⇒ static hosting, very low ops.
- **Dedup edge cases** — multi-part sermons, re-uploads, same-day multiples.
