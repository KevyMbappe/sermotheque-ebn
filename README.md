# Sermothèque EBN

> A durable, portable **system of record for the preaching of Église Bonne Nouvelle** — and the foundation for a future sermon app suite (web, mobile, TV).

**Église Bonne Nouvelle** is an église réformée baptiste in Poissy, France ([eglisebonnenouvelle.com](https://www.eglisebonnenouvelle.com)). Sermons are published on [YouTube](https://www.youtube.com/@eglisebonnenouvelle855) and [SoundCloud](https://soundcloud.com/ebn-paris).

> 📄 **Présentation en français** (pour les anciens & l'équipe média) : **[docs/SYNTHESE.md](docs/SYNTHESE.md)** · **[PDF](docs/SYNTHESE.pdf)** — état du projet, données, réalisations, feuille de route.
> *(Regénérer le PDF après modification : `python3 tools/md_to_pdf.py docs/SYNTHESE.md docs/SYNTHESE.pdf`.)*

## Why this exists

> **The catalog is the asset; every app, site, and platform is a replaceable window onto it.**

YouTube, SoundCloud, the website, and any future mobile/TV apps are all just *rendering surfaces*. The content — every sermon, richly indexed by scripture, speaker, series, and topic — is what compounds in value over decades. So the primary project is the **content system of record**: a clean, app-agnostic, version-controlled catalog plus the pipeline that keeps it fed. Apps come later, as thin clients over a great catalog.

## Status

🟢 **Planning complete · catalog built · enrichment validated at batch scale.** Catalog is data-driven and reproducible; a 30-sermon checkpoint (2026-06-17) confirmed cost and quality before the full pass.

| | |
|---|---|
| Catalog size | **517** distinct sermons (239 SoundCloud + 278 YouTube-only) |
| Enriched so far | **39 (~7.5%)** · voiceprints captured for **46** |
| Measured enrichment cost | **$0.0705/sermon** (Sonnet 4.6) ⇒ **~$36 for all 517** |
| Scripture coverage (OSIS) | **82%**, across 24 books of the Bible |
| Series auto-clustered | **26** (e.g. Épître aux Galates ×71, aux Hébreux ×28) |
| YouTube ↔ SoundCloud | largely **complementary** — corroborated matcher (decision #43) confirms 18 overlaps + 4 translations; true catalog = **union (517)** |

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
  scripture.py         Shared parsing primitives (OSIS book map, scripture/speaker parsing)
  parse_catalog.py     SoundCloud titles → structured metadata
  cluster_series.py    Group sermons into ordered series (run after the parser)
  match_youtube.py     Link YouTube videos to SC sermons; emit orphans
  fold_orphans.py      Fold orphans into one unified catalog (canonical schema)
  build.py             Run the whole pipeline in order (parse → match → fold → cluster)
data/
  raw/                 Raw YouTube/SoundCloud inventories (via yt-dlp)
  catalog/             The canonical dataset: catalog.json/.csv, series.json, youtube_orphans.json
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
- [ ] Full ASR enrichment pass across the 517 (transcripts, topics, summaries) — **~$36 on Sonnet**
- [ ] JSON Schema + WordPress import → website sermon library (first public deliverable)
- [ ] App suite (Expo: iOS · Android · Android TV · Fire TV) — see `docs/PRD.md`

## Key decisions

The full decision logs live in the spec docs. Highlights: SoundCloud is the catalog spine; scripture stored as canonical **OSIS** with a FR/EN parser; transcripts via ASR are the metadata engine; canonical data is git-versioned for durability; content is French-dominant with some English conference sermons (FR/EN/PT UI in the future apps).

---

*This repository is private. Long-term, ownership is intended to transfer to the church.*
