# PRD — Église Bonne Nouvelle App Suite

**Status:** Draft v2 — content-foundation-first reframe
**Last updated:** 2026-06-13
**Owner:** kevy@merca.team
**Existing site:** https://www.eglisebonnenouvelle.com (WordPress, theme `EBN_Version_Finale`)
**Sermon sources today:** YouTube (`@eglisebonnenouvelle855`) + SoundCloud

---

> **⚠️ Reframe (2026-06-13):** The **content system of record is now the primary project** — see [SERMOTHEQUE.md](SERMOTHEQUE.md). This app suite is a *downstream consumer* of the Sermothèque Catalog API. Build the catalog first; the apps are replaceable windows onto it. The decisions below stand, but they sit *under* the content system.

## 1. Thesis

A **dedicated, distraction-free room for the Word.** The congregation should reach for *our* app instead of opening YouTube and falling into the algorithm's autoplay rabbit hole. One home, three screens, three UI languages — serving one French-speaking body that comes from Brazil, Angola, Madagascar, and France.

This suite **supplements** the newly renovated website; it does not replace it. Everything must follow the site's existing warm, earth-toned design.

## 2. Goals & non-goals

**Goals**
- Give members a focused place to listen to / watch sermons on phone and TV.
- Make the full sermon back-catalog searchable and browsable (by series, speaker, scripture, date).
- Reuse the renovated WordPress site as the content backend and as the "web" surface.
- Be navigable by a culturally diverse congregation (FR/EN/PT UI).
- Be GDPR-clean and low-maintenance for a volunteer-run team.

**Non-goals (v1)**
- User accounts / social / community features.
- In-app payments or native giving.
- A separate standalone web app (the WP site fills this role).
- Per-sermon translation (all sermons are preached in French).

## 3. Surfaces & phasing

**Re-sequenced (2026-06-13): the CONTENT FOUNDATION ships first and stands alone — it upgrades the YouTube channel and the website *before any app exists*. The apps are just windows onto a catalog that is already rich. Approach is forward-first: nail the repeatable workflow for NEW sermons now; backfill the past later.**

**Phase 1 — Content Foundation** (standalone value, no app required)
- WordPress: add `Sermon` + `Service` content types (ACF) + verify REST API exposure.
- Extract design tokens from the live site into `shared-tokens.json`.
- Stand up the **metadata engine + thumbnail pipeline** (§10).
- **Forward-first rollout:**
  - **A (now):** repeatable per-sermon workflow for each new cut sermon the media team produces.
  - **B (soon):** backfill the small set of already-cut sermons (Videos tab).
  - **C (later, optional):** mine the large full-service archive (Live tab) to extract more sermons.
- Add a new **sermon-library section** to the WP website (first visible deliverable).

**Phase 2 — Apps** (onto the now-rich catalog)
- Expo monorepo → iOS, Android, Android TV, Fire TV.
- Features: library + search, background/offline audio, video, push, live, services archive.

| Surface | Phase | Tech |
|---|---|---|
| Web (WP sermon library) | 1 | Existing WordPress site + new section |
| iOS (phone) | 2 | React Native (Expo) |
| Android (phone) | 2 | React Native (Expo) |
| Android TV + Fire TV | 2 | React Native (Expo, `react-native-tvos`) |
| Apple TV | 3 (fast-follow) | React Native (Expo, tvOS) |

**Phase 3 — Expand (driven by usage data)**
- Apple TV; service-archive backfill; notes/Bible; devotionals; optional accounts for cross-device sync.

## 4. Architecture

```
WordPress (existing site)
├─ renovated public pages                  ← unchanged
├─ NEW: Sermon CPT (ACF)                    ← single source of truth
└─ WP REST API  ───────────────┐
                               │
shared-tokens.json (design)    │   shared TS: API client + models + i18n
        │                      │
 ┌──────┴────────┬─────────────┴──────────┐
 Expo mobile   Expo TV               WP web section
 (iOS+Android) (Android TV/Fire TV;  (sermon library
                Apple TV follow)      on the website)
```

**Monorepo layout (proposed)**
```
/apps
  /mobile        Expo app (phone UI: touch)
  /tv            Expo app (10-foot UI: remote/focus nav)
/packages
  /core          API client, data models, business logic
  /i18n          FR/EN/PT string catalogs (i18next)
  /tokens        design tokens extracted from the site
```
Shared core + i18n + tokens; two UI shells differing only in presentation/navigation.

## 5. Data model — two content types (WordPress CPTs via ACF)

**Critical distinction (2026-06-13):** YouTube holds two different things — full **Services** (Live tab) and isolated **Sermons** (Videos tab, cut by the media team). SoundCloud carries the clean isolated **sermon** audio. Different *scopes*, not the same content at different quality.

**Measured inventory (yt-dlp, 2026-06-13)** — files in `data/raw/`:
- YouTube **Videos** (cut sermons): **300** (~55–69 min)
- YouTube **Live** (services, "Culte Dimanche DD/MM"): **102** (~2 h)
- SoundCloud (clean sermon audio): **239** (~46–58 min)

The cut-sermon archive is **already large (300)** — extracting sermons from full services is therefore *not* needed for the catalog; backfill is a mostly-automated import. **SoundCloud is the canonical spine** of the sermon catalog: 74% of its titles are `Title | Scripture | (Pr. Speaker)`-structured (vs 20% on YouTube), so title-parsing gives a strong free first pass; YouTube videos are matched *in* by title/date.

### `Sermon` (rich — gets the full engine treatment)
| Field | Type | Notes |
|---|---|---|
| `title` | text | French |
| `date` | date | preached date |
| `speaker` | taxonomy | pastor / guest |
| `series` | taxonomy | conference / sermon series |
| `topics` | taxonomy | **curated, AI-bootstrapped** controlled vocabulary |
| `primaryScripture` | text | the main preaching text (the sermon's passage) |
| `scriptureRefs` | repeater | other passages referenced (auto-detected from transcript) |
| `summary` | text | AI-generated, human-confirmed |
| `transcript` | longtext + `.vtt` | from ASR on the clean audio; labeled "auto-generated" |
| `language` | enum | **default FR**; EN exists (conference sermons, e.g. Brian Borgman) |
| `youtubeId` | text | the **cut sermon** video (Videos tab), matched in by title/date |
| `soundcloudUrl` | text | clean sermon audio — **the spine + ASR/metadata source** |
| `thumbnail` | image | from the pipeline (§10) |

Content is French-dominant but **not single-language** — conference sermons in English exist, hence the optional `language` field.

### `Service` (light — archive, low metadata)
| Field | Type | Notes |
|---|---|---|
| `date` | date | service date |
| `preacher` | text | optional |
| `youtubeId` | text | full-service video / past live stream |
| `isLive` | derived | YouTube Live state for the "live now" card |

The Services type is the home of the **Live** feature's past streams.

**Open:** confirm whether the SoundCloud audio is trimmed to *only* the main sermon, or also captures the intro/offering preaching (affects how clean the engine's input is).

## 6. Feature detail (v1)

- **Library + search** — browse/filter by series, speaker, scripture, date; text search.
- **Audio** — stream + **offline download** (react-native-track-player); lock-screen / background controls; remembered playback position (on-device).
- **Video** — in-app YouTube playback.
- **Live + Services archive** — "we're live now" card opening the YouTube Live embed; push when the Sunday 10:30 stream starts; past services browsable as a light archive (distinct from the rich sermon library).
- **Push notifications** — new sermon posted; live started; (optional) Sunday reminder. Trigger: WP publish → webhook → Expo push.
- **Giving** — "Faire un don" button → existing WP donation page (in-app browser / external).

## 7. Cross-cutting requirements

- **Design** — single source of truth `shared-tokens.json` (colors, type, spacing, radii, logo) extracted from the live site; both app shells consume it. App must visibly match the site.
- **Languages** — UI fully **FR / EN / PT** via i18next; device-detected with manual override. Content stays French.
- **Accounts** — none; all user state on-device.
- **Privacy / GDPR** — **privacy-first, cookieless analytics** (Plausible/Umami-style or Expo privacy-respecting events); aggregate only, no PII, no consent banner; minimal privacy policy.
- **Updates** — Expo EAS: builds, store submission, and OTA updates for fixes without store review.

## 8. Operations & governance (who runs this when you're not around)

The core challenge: the suite must be operable by pastors/elders/deacons without the technical owner present. "Management" splits into two columns with opposite answers.

**Column A — Content operations** (recurring, weekly, must be church-run)
- **Interface:** a locked-down WordPress **Editor** experience — a custom role that hides all of WP except one "Sermons" menu with a clean, labeled ACF form. Paste YouTube link → title/thumbnail/date auto-fill → add speaker/series/scripture → Publish (~3 min, hard to break).
- **Roles (two tiers):**
  - **Publisher** (elders/deacons): add/edit sermons, go live. Safe, reversible, daily.
  - **Admin** (pastor + technical owner): all of the above + send manual push, edit series structure, manage access.
- **Notifications:** new-sermon push fires **automatically on publish**; "we're live" fires **automatically** when the YouTube stream starts; **manual push** (Admin-only) reserved for occasional announcements.

**Column B — Platform operations** (rare, technical, cannot be made pastor-operable)
- **Ownership (bedrock):** Apple Developer, Google Play, Amazon, WordPress, domain, and signing keys all registered **to the church as an organization**, under a church-owned email (e.g. `apps@eglisebonnenouvelle.com`), keys in a church-owned password manager. Technical owner is an **admin, not the owner** — removable and replaceable. *(Apple org account requires the church to be a legal entity with a D-U-N-S number — the association loi 1901 / cultuelle.)*
- **Continuity model:** minimize cadence + runbook + named backup.
  - Expo **EAS OTA updates** ship most fixes without a store submission; CI automates builds → real store releases ~1–2×/year.
  - A written **runbook** (step-by-step for each rare task) stored with the church.
  - One designated **technical backup** (volunteer dev or small agency on call).
- **Monitoring:** lightweight uptime monitor (UptimeRobot/BetterStack) pings the WP API + a health endpoint → auto-alerts the technical backup; calendar reminders for renewal time-bombs (certs/accounts). **Phase 2:** add Sentry error/crash tracking once usage is real.

**Build vs. buy:** decided to **build custom**. Turnkey platforms (Subsplash/Tithe.ly/Church Center) own column B for you, but cannot match the renovated site's design or deliver a real native TV app — abandoning them would mean abandoning this project's two core differentiators. Operability is instead engineered in (above).

## 9. Open items (not blockers — resolve before/during build)

- **Legal entity + D-U-N-S** — confirm the church's association status and obtain a D-U-N-S number for the Apple org account.
- **App name + icon** — "EBN"? Distinct identity vs. the website?
- **SoundCloud trim** — confirm whether SoundCloud audio is only the main sermon or also intro/offering preaching (titles suggest clean sermons).
- ~~Counts~~ **RESOLVED** (2026-06-13): 300 cut sermons / 102 services / 239 SC tracks; inventory in `data/raw/`.
- **YT↔SC matching** — pick the match key (title fuzzy-match + date) to link the 300 videos to 239 audio tracks; quantify unmatched.
- **Media-team workflow fit** — how the team currently cuts + publishes, so the pipeline plugs into their process.
- **Named technical backup** — identify the volunteer dev or agency for column B.
- **Who builds it / timeline / budget** — delivery question, separate from this design.

## 10. Content Foundation — metadata engine + thumbnail pipeline (Project B, now the core of Phase 1)

This is the heart of Phase 1: a repeatable per-sermon workflow that produces rich metadata **and** branded thumbnails in one pass. Operated by the **media team** (the "Publisher" role). Forward-first: built for new sermons, applied to backfill later.

### The per-sermon workflow (each new cut sermon)
1. **Ingest + parse title** — media team's cut sermon: clean `soundcloudUrl` (spine) + matched `youtubeId`. Parse the structured SoundCloud title (`Title | Scripture | (Pr. Speaker)`) to pre-fill title/primaryScripture/speaker/series for free (~74% yield).
2. **Transcribe** — ASR (Whisper large-v3-class) on the **clean SoundCloud audio** → transcript + `.vtt` subtitles, labeled "auto-generated." (Clean source = no hymn/offering pollution.)
3. **AI suggestions** — an LLM reads the transcript and proposes `primaryScripture`, `scriptureRefs`, `topics` (from the curated vocabulary), and a `summary`.
4. **Human pass** — in one review screen the operator confirms the AI suggestions **and** picks the thumbnail frame from the top 3. (Confirm-don't-type.)
5. **Thumbnail composite** — branded overlay over the chosen frame → 1280×720 PNG.
6. **Publish** — write the `Sermon` to WP; push the thumbnail to YouTube via the Data API; (auto) notification fires.

### Thumbnail decisions
- **One 16:9 template, two outputs** — serves the YouTube thumbnail *and* the app card, same data.
- **Video-frame-led + consistent branded overlay** (gradient scrim + title/speaker/scripture in EBN type + logo). Overlay carries brand; frame carries authenticity.
- **Frame selection:** `yt-dlp` → `ffmpeg` sample frames (skip intros/black/transitions) → CV heuristics (sharpness, face + eyes-open + frontal, exposure) discard junk → **vision model reranks**. Medium difficulty, not research. *(For backfill from full services, sampling should target the sermon segment.)*
- **Human check:** top-3 candidates in a throwaway local review screen; click the winner (~5–10s).
- **Publish to YouTube:** Data API `thumbnails.set` after approval; one-time channel-owner OAuth; quota a non-issue.

### Topic taxonomy
- LLM reads the whole transcript corpus → **proposes a starter topic list** → human curates once into a canonical vocabulary (~30–60 topics) → per-sermon topics auto-suggested from it and confirmed.

### Sequencing & ops caveat
- **Ship 1st:** the workflow as a mostly-offline pipeline for new + already-cut sermons (no hosting beyond ASR/LLM API calls).
- **Fast-follow:** folding frame-selection into the weekly WP publish form turns the pipeline into a small **hosted service** WP calls on demand → joins **Column B** (host + monitor). Must **degrade gracefully** — if it's down, publishing still succeeds and the thumbnail/metadata backfills later; it never blocks a sermon going live.
- **Later/optional:** mining the full-service archive (locating + cutting the sermon out of each service) is the heavy retroactive work — explicitly deferred, never a launch dependency.

---

### Decision log (from grilling session, 2026-06-13)
<!-- When a decision changes, append a numbered entry and update affected sections; see the Maintenance protocol in CLAUDE.md. -->

1. Structured catalog (not a feed reader).
2. Headless WordPress as CMS.
3. Bulk import once, then manual-assisted weekly.
4. Mobile + TV first; web = WP site.
5. Native TV app (no casting); Android TV + Fire TV first, Apple TV fast-follow.
6. v1 features: library+search, offline/background audio, video, push, live.
7. No accounts in v1.
8. Giving = link to WP donation page.
9. Expo (dev builds).
10. Extract lightweight design tokens.
11. UI in FR/EN/PT; 12. content single-language (French).
13. Privacy-first, no-consent analytics.
14. Operability is a first-class requirement → stay custom-build (not turnkey vendor).
15. Content publishing via locked-down WP admin + guided auto-fill form.
16. Two roles: Publisher (elders/deacons) + Admin (pastor + technical owner).
17. All accounts/keys owned by the church as an organization; technical owner is a removable admin.
18. Platform-ops continuity: minimize cadence (EAS OTA) + runbook + named technical backup.
19. Notifications: auto on publish / auto on live; manual push (Admin-only) for announcements.
20. Monitoring: lightweight uptime + alert to backup now; Sentry in Phase 2.

**Project B (thumbnails):**
21. One 16:9 template, two outputs (YouTube + app card).
22. Video-frame-led background + consistent branded overlay.
23. AI frame selection (yt-dlp/ffmpeg + CV heuristics + vision-model rerank); human picks from top 3.
24. Overlay text from the WP catalog; fused with Phase-0 import via one unified back-catalog pass.
25. Publish via YouTube Data API after approval.
26. Going forward: folded into the weekly publish form; retro batch ships first as an offline script, weekly integration is a hosted service that must degrade gracefully.

**Content foundation reframe (supersedes #3 "bulk import first"):**
27. CONTENT FOUNDATION ships first and standalone (upgrades YouTube + website before any app); apps move to Phase 2.
28. Forward-first: nail the repeatable workflow for NEW sermons now; backfill already-cut sermons soon; mine the full-service archive later (optional).
29. Two content types: rich `Sermon` (full engine) + light `Service` (archive, home of Live). YouTube has both (Videos vs Live tab); they are different scopes.
30. Metadata source = ASR on the CLEAN SoundCloud sermon audio (avoids whole-service pollution), not the YouTube full-service transcript.
31. Transcripts: ASR now as the metadata engine (auto-suggest scripture/topics/summary); correct opportunistically, not exhaustively.
32. Topics: curated vocabulary, AI-bootstrapped from the corpus, then auto-suggested + confirmed per sermon.
33. Media team = the Publisher role; the pipeline must fit their existing cut-and-publish process.

**Measured inventory + refinements (yt-dlp, 2026-06-13; data in `data/`):**
34. Counts: 300 cut-sermon videos, 102 service streams, 239 SoundCloud tracks (402 YT total). Assumption "few cut sermons" was wrong — the sermon archive is already large; service-mining is NOT needed for the catalog; backfill is a mostly-automated import.
35. SoundCloud is the canonical catalog spine (74% structured titles vs 20% on YT); title-parsing gives a free first-pass of title/scripture/speaker; YT videos matched in by title/date.
36. Content is NOT single-language — English conference sermons exist → add optional `language` field (default FR). (Softens #12.)
