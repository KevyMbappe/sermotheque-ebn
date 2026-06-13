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

## 6. Backfill plan (measured inventory — files in `/data`)

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

**M1 first-pass catalog — DONE (2026-06-13).** `scripts/parse_catalog.py` parses the 239 SoundCloud titles → `data/catalog.json` + `data/catalog.csv`. Coverage (titles only, no ASR):
- Scripture (OSIS): **196/239 (82%)**, 80% high-confidence, across **24 books**.
- Clean title: 87% · Speaker: 26 named (mostly the regular pastor is untagged) · Series part: 34 · English: 0 (SoundCloud is FR-only).
- Distribution reveals systematic expository series: **Galates 72, Hébreux 28, Genèse 16, Jacques 14, Ézéchiel 11**.
- Known limitations carried to enrichment: the 43 refless items (intros/Q&A/topical), speaker inference for the regular preacher, multi-range verses approximated as a span.

**M1b series clustering — DONE (2026-06-13).** `scripts/cluster_series.py` → `data/series.json` + enriches catalog. **22 series, 81% of sermons placed**, ordered by chapter:verse. Expository: Épître aux Galates (69), aux Hébreux (28), de Jacques (14), Genèse (13), Ézéchiel (11)… Thematic: Joie chrétienne, Noël le plus glorieux des mystères, Fruit de l'Esprit… Pipeline order is `parse_catalog.py` → `cluster_series.py`.

**Git — DONE (2026-06-13).** Repo initialized (branch `main`); the canonical dataset is now version-controlled per the durability decision. Initial commit `e2d3218`.

## 8. Resolved design decisions (grilled 2026-06-13)
- **Scripture:** canonical **OSIS** book IDs (e.g. `Rom.8.1-8.4`) + a FR/EN parser; display localized, query canonical. Powers browse-by-book.
- **EN/FR pairing:** **independent** Sermon records linked by `translation_of` (each keeps its own media/transcript/thumbnail).
- **Versioning/audit:** **git history of the flat-file export** is the audit trail; live store is last-writer-wins. Zero extra infra.
- **Search:** **prebuilt static index** (FlexSearch/lunr/Pagefind) regenerated on export; near-zero ops, no server. Upgrade to a managed search server later only if scale demands.
- **Topic labels:** translated **FR + EN + PT** (bounded ~30–60 list); matches the trilingual UI.
- **YT↔SC matching (backfill):** **fuzzy title + date window**; high-confidence auto-link, low-confidence to the completeness dashboard; orphans (EN-only videos) flagged, not forced.

### Still open (lighter — resolve during build)
- **Canonical hosting** — where the git export repo + static serving live (church-owned, per [PRD.md](PRD.md) §8 ownership model). Static index ⇒ static hosting, very low ops.
- **Dedup edge cases** — multi-part sermons, re-uploads, same-day multiples.
