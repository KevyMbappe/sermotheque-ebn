# Sermothèque EBN

> A durable, portable **system of record for the preaching of Église Bonne Nouvelle** — and the foundation for a future sermon app suite (web, mobile, TV).

**Église Bonne Nouvelle** is an église réformée baptiste in Poissy, France ([eglisebonnenouvelle.com](https://www.eglisebonnenouvelle.com)). Sermons are published on [YouTube](https://www.youtube.com/@eglisebonnenouvelle855) and [SoundCloud](https://soundcloud.com/ebn-paris).

> 🌐 **Le catalogue en ligne : https://kevymbappe.github.io/sermotheque-ebn/** — 131 prédications enrichies, avec lecteur, chapitres horodatés et transcription synchronisée. Le site est une *projection* du dataset canonique : il se met à jour tout seul à chaque passe d'enrichissement (décisions #54/#55).
>
> 📄 **Présentation en français** (pour les anciens & l'équipe média) : **[docs/SYNTHESE.md](docs/SYNTHESE.md)** · **[PDF](docs/SYNTHESE.pdf)** — état du projet, données, réalisations, feuille de route.
> *(Regénérer le PDF après modification : `python3 tools/md_to_pdf.py docs/SYNTHESE.md docs/SYNTHESE.pdf`.)*

## Why this exists

> **The catalog is the asset; every app, site, and platform is a replaceable window onto it.**

YouTube, SoundCloud, the website, and any future mobile/TV apps are all just *rendering surfaces*. The content — every sermon, richly indexed by scripture, speaker, series, and topic — is what compounds in value over decades. So the primary project is the **content system of record**: a clean, app-agnostic, version-controlled catalog plus the pipeline that keeps it fed. Apps come later, as thin clients over a great catalog.

## Status

🟡 **Catalog built · backfill in flight (paused).** The pipeline is validated end to end and the catalog is reproducible from raw. The catalog-wide capture pass ran to ~27% and **stopped there**; resuming it is the critical path (see the roadmap).

| | |
|---|---|
| Catalog size | **517** distinct sermons (239 SoundCloud + 278 YouTube-only) |
| Transcribed (one-shot, audio) | **139/517 (~27%)** — `.txt` + `.vtt` committed · voiceprints for **217** |
| Enriched (re-runnable, text) | **139/517 (~27%)** — 126 SoundCloud, 13 YouTube |
| Speaker attribution | 100 `audio-fingerprint` · 45 `title` · 331 `default-rule` · 41 blank |
| Measured enrichment cost | **$0.0705/sermon** (Sonnet 4.6) ⇒ **~$27 for the 378 remaining** |
| Scripture coverage (OSIS) | **196/239 (82%)** on the SoundCloud spine · **215/517 (42%)** across the union, 28 books |
| In-body citations (OSIS) | **1 243/1 243 normalised (0 failures)** on the 139 enriched rows → `scripture_refs_osis`; **54 distinct books** reachable via body citations vs 22 via the main passage (decision #56) |
| Topic vocabulary (#57) | **44 curated categories** · 98% of the 1 086 free-text labels classified → `topics_canonical`, derived on every build |
| Series auto-clustered | **26** (e.g. Épître aux Galates ×71, aux Hébreux ×28) |
| YouTube ↔ SoundCloud | largely **complementary** — corroborated matcher (decision #43) confirms 18 overlaps + 4 translations; true catalog = **union (517)** |

> ⚠️ **Audit this before resuming the pass:** 79 ids hold a voiceprint but no committed transcript, though `build_entry` writes both from the same download. See `docs/SERMOTHEQUE.md` §7b (M5u).

## Architecture

```
AUTHORING (write)   WordPress admin (humans) + the pipeline (machines)      — replaceable
      │  write Sermon/Service records
      ▼
CANONICAL (own) ★   clean, app-agnostic, git-versioned dataset + API + search — the durable asset
      │  everything reads from here
      ▼
CONSUMPTION (read)  website sermon library · mobile/TV apps · thumbnail pusher — replaceable
```

WordPress **authors but does not own** the data. The canonical dataset (`data/`) is the source of truth and outlives any single shell.

## Repository layout

```
CLAUDE.md              Agent/contributor front door — read this to get oriented fast
docs/
  SERMOTHEQUE.md       ★ Spec for the content system of record (the primary project)
  PRD.md               App suite spec (web/mobile/TV) — a downstream consumer
pipeline/
  scripture.py         Shared parsing primitives (OSIS book map, scripture/speaker parsing,
                       + citation → OSIS normalisation for in-body refs, #56)
  parse_catalog.py     SoundCloud titles → structured metadata
  cluster_series.py    Group sermons into ordered series (run after the parser)
  match_youtube.py     Link YouTube videos to SC sermons; emit orphans
  fold_orphans.py      Fold orphans into one unified catalog (canonical schema)
  build.py             Run the whole pipeline in order (parse → match → fold → cluster)
data/
  raw/                 Raw YouTube/SoundCloud inventories (via yt-dlp)
  catalog/             The canonical dataset: catalog.json/.csv, series.json, youtube_orphans.json,
                       enrichment.json, voiceprints.json, speakers.json, transcripts/
apps/
  web-poc/             Live — static React/Vite window onto the catalog (decisions #54/#55),
                       deployed to GitHub Pages by .github/workflows/deploy-poc.yml
```

## Quickstart

Rebuild the catalog from the raw inventories (pure-stdlib Python 3, no dependencies):

```bash
python3 pipeline/build.py    # runs parse → cluster → match, writes data/catalog/*
```

Re-pulling inventories requires a recent `yt-dlp` (≥ 2026.x).

## Roadmap

- [x] Plan & specs (decision logs in `docs/SERMOTHEQUE.md` / `docs/PRD.md`)
- [x] **M1** — first-pass catalog from SoundCloud titles
- [x] **M1b** — series clustering (expository + thematic)
- [x] **M2** — YouTube ↔ SoundCloud matching (found: largely complementary, not a mirror)
- [x] **M2b** — YT↔SC dedup via duration fingerprint, full coverage
- [x] **M3** — ASR + LLM enrichment spike (PASS — see `docs/research/METHODOLOGY.md`)
- [x] **M4** — fold YT orphans into one unified catalog (canonical schema, 26 series)
- [x] **M5** — per-sermon enrichment pipeline (`build_entry`) + timestamps + live cost tracking
- [x] **M5h** — matcher hardening: duration only corroborates (18 overlaps + 4 translations; **union 517**; decision #43)
- [x] **Enrichment writeback layer** (decision #44) — id-keyed store survives rebuilds
- [x] **Production runner + default-speaker rule** (decision #45) — resumable, logfile, live cost
- [x] **Voiceprint capture** (decision #46) — Resemblyzer embedding captured in-pass, id-keyed store
- [x] **M5n — 30-sermon checkpoint** (decision #47): 39 enriched (~7.5%), 46 voiceprints, **$0.0705/sermon ⇒ ~$36/517**
- [x] **M5o — language from audio** (decision #48): forced-fr default → retry-en on garbage → label from transcript content; YouTube download retry
- [x] **M5p–q — audio speaker attribution + series priors** (decisions #49–#52): all 5 preachers' voices learned (David, Loïc→Hébreux, Stephan→Ézéchiel, Nathanaël→Jacques, Christian→Jean); 100 rows `audio-fingerprint`; LOO 99% among the 5
- [x] **M5s — capture/enrich decoupled** (decision #52): `--no-enrich` capture-only pass ($0 API) + transcript-cache-aware enrich (no re-ASR); rebuild preserves attribution
- [x] **M5t — frozen record contract** (decision #53): `schema.py` + `sermon.schema.json` (WP-import contract), validated in `build.py`; **Sonnet-only locked**
- [x] **M5u — capture batch started** (2026-06-20): 139 transcripts + 217 voiceprints banked at $0 API — **pass paused at ~27%**
- [x] **M5v — enrich from disk** (2026-06-22): store 39 → **139 enriched**, no re-ASR, ~$7 on Sonnet
- [x] **M5w — in-body citations normalised to OSIS** (2026-08-01, decision #56): `scripture_refs_osis`, derived on every writeback; 1 243/1 243 parsed, 54 books reachable — unblocks the inverted index / browse-by-passage
- [ ] **Finish the capture pass** — the only irreversible work; resume `run_enrichment.py --no-enrich` (Apple Silicon required for mlx-whisper)
- [ ] **Enrich the remaining 378** — from committed transcripts, no re-ASR (**~$27 on Sonnet**)
- [x] **POC web DEPLOYED** (2026-08-01, decisions #54/#55) — **https://kevymbappe.github.io/sermotheque-ebn/** · 131 enriched sermons, player + chapter deep-links + synced transcript; republishes itself when `data/catalog/**` changes. Remaining polish: the YouTube IFrame path and an EN sermon (`docs/plans/WEB-POC-STATUS.md`)
- [x] **M6d–e — POC polished** (2026-08-01): OSIS citations (#56) + shareable `?t=` links + per-sermon link previews (131 pre-rendered pages) + **browse-by-passage** (54 books)
- [x] **M6f — curated topic vocabulary** (2026-08-01, decision #57): 44 categories, 98% coverage, browse-by-theme on the site
- [x] **M6g — POC polish** (2026-08-01): weighted full-text search with match snippets, printable home-group sheet, 1200×630 link-preview cards, stray Xcode scaffold removed
- [x] **M6h — sermon page restructured** (2026-08-02): listen-first order, collapsible sections, sticky player block; the page is a summary you unfold instead of a wall of text
- [x] **M6i — full-text search over the transcripts** (2026-08-04, decision #59): prefix-sharded static index (338 shards, 0.6 KB median per query) — a search now returns **moments**, not just pages; 77% of the indexed vocabulary exists nowhere in the editorial fields
- [x] **M6j — the POC's statement of purpose** (2026-08-04, decision #58): a permanent playground, not a first deliverable nor a throwaway — `apps/web-poc/README.md`
- [ ] WordPress import → sermon library on the church's own site (the POC above is a demo, not its replacement — see #54)
- [ ] App suite (Expo: iOS · Android · Android TV · Fire TV) — see `docs/PRD.md`

## Key decisions

The full decision logs live in the spec docs. Highlights: SoundCloud is the catalog spine; scripture stored as canonical **OSIS** with a FR/EN parser; transcripts via ASR are the metadata engine; canonical data is git-versioned for durability; content is French-dominant with some English conference sermons (FR/EN/PT UI in the future apps).

---

*This repository is **public** (since 2026-08-01) — which makes GitHub Pages free for the web POC, and means the catalog, the transcripts, and the pipeline are readable by anyone. The sermons themselves are already public on YouTube and SoundCloud. Long-term, ownership is intended to transfer to the church.*
