# Sermothèque EBN — Sermon & Service System of Record

**Status:** Draft v1 (for grilling)
**Last updated:** 2026-06-13
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
| `transcript_ref` | file (`.txt` + `.vtt`) | ASR output, labeled "auto-generated" |
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

**M3 ASR + LLM enrichment spike — DONE (2026-06-13).** Transcribed one sermon (mlx-whisper `large-v3-turbo`, ~6× real-time, local/free) and enriched it. **PASS** — excellent French ASR (cosmetic artifacts only), accurate zero-hallucination topics/summary, and it *recovered series context the title lacked* (Confession de foi 1689, ch. 8). Refined division of labor: **title → primary scripture; transcript → topics/summary/series/search**. Speaker inference is the weak spot (use a default rule, not ASR). Full write-up: `docs/spike-asr-2026-06-13.md`.

**M3b ASR bigger sample (n=8, 2023→2026) — DONE (2026-06-13).** 8 sermons across the archive (incl. oldest + multiple speakers): **zero failures, uniformly high quality across all eras**. Errors are **systematic** (foi→fois, le→les, Dieu→dieux for the regular pastor) → cheap regex post-clean. Different (native-FR) speakers transcribe even cleaner (artifact = weak speaker fingerprint). **Speed:** ~6–7× real-time ⇒ 239 SC sermons ≈ **~30+ h local compute** (chunks/parallel/cloud, not one overnight). Verdict: green-light the full pass, with a regex normalization step + a default-speaker rule.

**M4 fold orphans → unified catalog — DONE (2026-06-13).** `pipeline/fold_orphans.py` merges the 239 SoundCloud records + 228 YouTube orphans into **one catalog of 467 records** with a uniform canonical schema (`id`, `source`, `media`, enrichment placeholders). Pipeline order is now **parse → match → fold → cluster** (`build.py`); series clustering runs over the union → **25 series** (new ones surfaced from YT/conference content). `catalog.csv` is now the flattened 467-row export written by the final step. *(Not yet folded: the 102 Live `Service` records — a separate light type.)*

## 8. Resolved design decisions (grilled 2026-06-13)
- **Scripture:** canonical **OSIS** book IDs (e.g. `Rom.8.1-8.4`) + a FR/EN parser; display localized, query canonical. Powers browse-by-book.
- **EN/FR pairing:** **independent** Sermon records linked by `translation_of` (each keeps its own media/transcript/thumbnail).
- **Versioning/audit:** **git history of the flat-file export** is the audit trail; live store is last-writer-wins. Zero extra infra.
- **Search:** **prebuilt static index** (FlexSearch/lunr/Pagefind) regenerated on export; near-zero ops, no server. Upgrade to a managed search server later only if scale demands.
- **Topic labels:** translated **FR + EN + PT** (bounded ~30–60 list); matches the trilingual UI.
- **YT↔SC matching (backfill):** **fuzzy title + date window**; high-confidence auto-link, low-confidence to the completeness dashboard; orphans (EN-only videos) flagged, not forced.

### Decision (added)
- **#37 (2026-06-13):** The catalog is the **UNION of SoundCloud + YouTube** (**467** distinct sermons), not the SC spine alone. SC = clean French expository audio (239); YouTube adds conference content (~45) + English versions + SC-absent French sermons. YT↔SC are largely *complementary*: with full duration coverage (239/239), duration-fingerprint matching (YT ≈ SC + 51 s) confirms **61** same-language overlaps + **11** translations; the remaining **228** YT videos are net-new.

### Still open (lighter — resolve during build)
- **YT↔SC true overlap** — dedup the ~215 French YT orphans against SC needs a stronger signal than titles: re-pull `duration`+`upload_date` (both platforms) and match on those, or use embeddings/audio fingerprint.
- **Canonical hosting** — where the git export repo + static serving live (church-owned, per [PRD.md](PRD.md) §8 ownership model). Static index ⇒ static hosting, very low ops.
- **Dedup edge cases** — multi-part sermons, re-uploads, same-day multiples.
