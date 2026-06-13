# Spike — ASR + LLM enrichment (1 sermon) · 2026-06-13

**Question:** can we transcribe a French sermon and have an LLM propose topics/summary/scripture at *confirm-don't-type* quality? (The biggest unproven assumption of the project.)

**Verdict: PASS.**

## Method
- Sermon: *« La doctrine de l'incarnation de Christ | Luc 1:26-38 »* (newest SoundCloud track).
- Audio via `yt-dlp -x`; 15-min slice → 16 kHz mono WAV (`ffmpeg`).
- ASR: **mlx-whisper `large-v3-turbo`** (Apple Silicon), `--language fr`.
- Enrichment: an LLM reads the transcript and proposes structured metadata.

## Results
- **Speed:** 15 min transcribed in **2m13s** (~6× real-time). Full 56-min sermon ≈ 8–9 min. **Local, free, no API.**
- **ASR accuracy:** excellent on theological French (médiateur, incarnation, naissance virginale, rédemption, Confession de foi, Trinité…). Systematic but cosmetic artifacts only: homophones (`foi`→`fois`), spurious articles (`le Fils`→`les Fils`) — consistent with a Lusophone-accented French. Meaning fully intact.
- **Enrichment from the transcript alone:**
  - topics: Incarnation, Naissance virginale, Christ médiateur, Christologie, Rédemption, Alliance de grâce, Confession de foi 1689, Trinité
  - summary: accurate, zero hallucination, every claim traceable to the audio
  - **recovered series context the title lacks:** *Confession de foi (1689), ch. 8 — De Christ le Médiateur*

## Bigger sample (n=8, spanning 2023-10 → 2026-06)
Transcribed 8-min slices of 8 sermons spaced across the SoundCloud archive (oldest = *Leçon — Baptême*, 2023-10-26), incl. different speakers.
- **Zero failures; quality uniformly high across all eras** — old audio did NOT degrade results.
- **Errors are systematic, not random** (regular pastor): `confession de foi`→`fois`, `le Seigneur`→`les Seigneurs`, `de/le Dieu`→`des/les dieux`. → fixable with a small **regex post-clean dictionary**, no model change.
- **Multiple speakers, all handled well**; #175/#210 are a different native-FR preacher, transcribe even cleaner (artifact absent) → the artifact is a **weak speaker fingerprint**.
- **Enrichment-ready every time** (passage, theme, series — often series context beyond the title).
- **Speed (corrected on a FULL sermon):** 3,389 s audio → 221 s ⇒ **~15× real-time** (the ~6–7× from short slices was inflated by one-time model-load overhead). ⇒ 239 SC sermons ≈ **~15 h local compute** — feasible as a couple of overnight runs.

## Key learnings (feed into the enrichment design)
1. **Division of labor:** the **title** is the best source of the *primary scripture* (already 82% parsed); the **transcript** is for *topics, summary, series context, full-text search* — complementary, not redundant. (In a 15-min intro the preacher may not yet have read the Bible passage.)
2. **Speaker inference is the weak spot** — not reliable from text alone. Solve with a default rule (untagged ⇒ regular pastor) or voice fingerprinting, not ASR.
3. **Feasibility:** full transcription of ~239 sermons = a one-time overnight local batch; LLM enrichment = one cheap call per sermon. Correct opportunistically (decision: don't hand-polish every transcript).
