# Enrichment model — bake-off, cost, and pricing reference

**Last updated:** 2026-06-14 · Decisions [#40](SERMOTHEQUE.md) (model + cost) and #41 (pluggable ASR).

The enrichment step (`pipeline/enrich.py`) makes **one Claude API call per sermon** — it reads the
ASR transcript and returns a French summary, topics, the primary passage, body-cited scripture
refs, and any series context. This doc records *which model* we run it on and *what it costs*, with
the measured evidence.

## TL;DR

- **Default model: `claude-sonnet-4-6`. ~$0.06/sermon measured ⇒ ~$12 for the 239 SoundCloud sermons, ~$23 for the full 467-record union.** One-time, not recurring.
- **Haiku 4.5 is the budget fallback** — ~⅓ the cost, nearly as good, but it slips on French precision (see below).
- A full transcript is ≈ **13–16k input tokens + ~1.5k output**; that's the whole per-call cost (no caching needed — each sermon is a distinct one-shot call).

## Claude pricing reference (per 1M tokens, 2026-06)

Authoritative figures from the `claude-api` skill (`shared/models.md`). The enrich step's input is the transcript (~13–16k tok); output is the JSON (~1.5k tok).

| Model | ID | Input $/1M | Output $/1M | ≈ cost / sermon¹ |
|---|---|---:|---:|---:|
| Claude Haiku 4.5 | `claude-haiku-4-5` | $1.00 | $5.00 | **~$0.018** |
| **Claude Sonnet 4.6** ⭐ | `claude-sonnet-4-6` | $3.00 | $15.00 | **~$0.053** |
| Claude Opus 4.8 | `claude-opus-4-8` | $5.00 | $25.00 | ~$0.09 |
| Claude Fable 5 | `claude-fable-5` | $10.00 | $50.00 | ~$0.18 |

¹ For a ~16k-input / ~330-output enrichment call (the measured shape below). Opus/Fable shown for scale — overkill for confirm-don't-type metadata; not used.

## The bake-off (2026-06-14)

One rich sermon — **"La doctrine de l'incarnation de Christ" (Luc 1:26-38)**, `sc-2338530545`, full transcript — enriched by both candidate models back-to-back (`cache/haiku_vs_sonnet.py`, gitignored). Measured token usage × the pricing above:

| | Haiku 4.5 | Sonnet 4.6 |
|---|---|---|
| **Cost (this sermon)** | **$0.0177** (15 983 in / 347 out) | **$0.0527** (15 984 in / 314 out) |
| Latency | 5.6 s | 7.8 s |
| Scripture refs | Jean 1:1-14, Galates 4:4, Romains 8:3, Phil 2:6-8, Héb 2:14-17, 1 Jean 4:2-3, Luc 24:39, Malachie 4:2, 1 Tim 3:16 — **excellent** | Jean 1:1, Jean 1:14, Galates 4:4, Romains 8:3, Phil 2:6-8, Héb 2:14, Héb 2:17, Luc 24:39, Malachie 4:2, 1 Jean 4:2 — **excellent** |
| Heresies | *"protéger cette doctrine contre les hérésies"* — **generic** | *"docétisme, nestorianisme, modalisme"* — **named precisely** |
| French quality | slips: *"essential"*, *"necessaires"* (anglicisms/typos); series label *"Les Christs, les médiateurs"* malformed | clean throughout; series *"Confession de foi ch.8 — Christ Médiateur"* |

> **The $0.07 you saw on the platform was *both* runs combined** ($0.0177 + $0.0527 = $0.0704), not Haiku alone. Sonnet is ~3× Haiku, exactly as the pricing predicts.

### Verdict — Sonnet 4.6, with Haiku as fallback

Both models are faithful, zero-hallucination, and find essentially the same scripture. The gap is **French theological precision**: Sonnet names heresies correctly and writes clean French an elder will read without wincing; Haiku stays generic and slips anglicisms. For a church catalog where the output is *shown to elders and published*, that margin is worth the extra ~$10 across the whole catalog (~$23 vs ~$8 on Haiku). Haiku stays documented as the budget option for bulk/throwaway runs.

To switch models, pass `--model claude-haiku-4-5` to `build_entry.py`, or `make_enricher(model=...)`.

## Reproduce

```bash
./.venv/bin/python cache/haiku_vs_sonnet.py   # prints both outputs + measured cost (needs ANTHROPIC_API_KEY)
```
