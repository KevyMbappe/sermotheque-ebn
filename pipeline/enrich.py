#!/usr/bin/env python3
"""
Sermothèque EBN — enrichment step (the second injected, external step).

make_enricher(...) builds the real enrich_fn(transcript, parsed) -> dict, which makes ONE
Claude API call per sermon and returns structured metadata the title can't give us:
topics, a French summary, scripture references heard in the audio, and any series context.

`anthropic` is imported lazily inside make_enricher so the pipeline core (and the test suite)
import without the SDK installed. Tests inject a fake enricher instead of calling this.
"""

# Controlled topic vocabulary is bootstrapped/curated elsewhere; passed in to keep topics consistent.
ENRICH_SCHEMA = {
    "type": "object",
    "properties": {
        "description": {"type": "string",
                        "description": "ONE punchy sentence (≤30 words) to show under the video — distinct from the summary; a hook, not a recap."},
        "invitation": {"type": "string",
                       "description": "2-4 sentence warm, SOBER invitation to listen (blogger-style 'why listen'). Inviting but substantive — no marketing clichés, no 'plongez dans', no empty superlatives."},
        "summary": {"type": "string", "description": "2-3 sentence French summary, faithful to the audio."},
        "key_points": {"type": "array", "items": {"type": "string"},
                       "description": "3-6 short bullets tracing the sermon's main movements/arguments."},
        "chapters": {"type": "array",
                     "description": "3-7 sections of the sermon, in order, for player navigation.",
                     "items": {"type": "object", "additionalProperties": False,
                               "required": ["title", "anchor"],
                               "properties": {
                                   "title": {"type": "string", "description": "short section title"},
                                   "anchor": {"type": "string", "description": "a phrase copied VERBATIM (exact words, IN THE TRANSCRIPT'S OWN LANGUAGE — do NOT translate it) from the transcript where this section begins — used to locate its timestamp."}}}},
        "topics": {"type": "array", "items": {"type": "string"},
                   "description": "4-8 theological tags, broad to specific — both subjects and the precise doctrines taught (e.g. 'Christologie', 'Union hypostatique', 'Prière'). Prefer the controlled vocabulary; most specific last."},
        "references": {"type": "array", "items": {"type": "string"},
                       "description": "People/works/confessions actually CITED (e.g. 'Jean Calvin', 'Confession de foi de 1689', 'Augustin'). Confirm, don't invent; empty if none."},
        "key_quotes": {"type": "array", "items": {"type": "string"},
                       "description": "1-3 striking sentences copied VERBATIM (exact words, IN THE TRANSCRIPT'S OWN LANGUAGE — do NOT translate) from the transcript — used for clips/search; timestamps are attached afterwards."},
        "questions": {"type": "array", "items": {"type": "string"},
                      "description": "2-4 reflection/discussion questions for a small group (these are study aids — generated, not quoted)."},
        "primary_scripture": {"type": "string", "description": "Main passage preached (e.g. 'Luc 1:26-38'), or empty."},
        "scripture_refs": {"type": "array", "items": {"type": "string"},
                           "description": "Other passages cited in the sermon."},
        "series_hint": {"type": "string", "description": "Series/study context mentioned (e.g. 'Confession de foi ch.8'), or empty."},
    },
    "required": ["description", "invitation", "summary", "key_points", "chapters", "topics",
                 "references", "key_quotes", "questions",
                 "primary_scripture", "scripture_refs", "series_hint"],
    "additionalProperties": False,
}

# Claude API pricing, $ per 1M tokens (input, output) — keep in sync with
# docs/ENRICHMENT-MODEL.md. Used to report live cost; no effect on the call itself.
PRICES = {
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-haiku-4-5": (1.0, 5.0),
    "claude-haiku-4-5-20251001": (1.0, 5.0),
    "claude-opus-4-8": (5.0, 25.0),
}


def cost_of(model: str, in_tok: int, out_tok: int) -> float:
    """USD for one enrichment call, from the measured token usage."""
    pin, pout = PRICES.get(model, (0.0, 0.0))
    return in_tok / 1e6 * pin + out_tok / 1e6 * pout


PROMPT = """Tu enrichis le catalogue de prédications d'une église réformée baptiste francophone.
À partir de la TRANSCRIPTION (en français OU en anglais, générée automatiquement — ignore les
coquilles d'ASR), renvoie un JSON. Rédige tout en français — SAUF les champs `anchor` (dans
chapters) et `key_quotes`, qui sont des copies TEXTUELLES de la transcription et doivent rester
dans la langue de la transcription (ne les traduis pas, sinon on ne peut pas retrouver leur minutage):
- description: UNE phrase accrocheuse (≤30 mots) à afficher sous la vidéo (une accroche, pas un résumé);
- invitation: 2-4 phrases chaleureuses mais SOBRES, donnant envie d'écouter (pas de clichés marketing, pas de 'plongez dans');
- summary: un résumé fidèle de 2-3 phrases;
- key_points: 3-6 points clés retraçant le déroulé;
- chapters: 3-7 sections en ordre, chacune avec un titre (title) et une phrase d'ancrage (anchor) copiée TEXTUELLEMENT de la transcription au début de la section (servira à retrouver son minutage);
- topics: 4-8 étiquettes théologiques, du général au précis (sujets ET doctrines exposées, ex: Christologie, Union hypostatique, Prière); privilégie le vocabulaire contrôlé;
- references: personnes/œuvres/confessions réellement CITÉES — n'invente pas, vide si aucune;
- key_quotes: 1-3 phrases marquantes copiées TEXTUELLEMENT (mots exacts) de la transcription;
- questions: 2-4 questions de réflexion pour un groupe (aides générées);
- primary_scripture, scripture_refs, series_hint.
Confirme, n'invente pas (sauf invitation/questions, qui sont rédigées). {vocab}

Titre (indice): {title}
TRANSCRIPTION:
{transcript}
"""


def make_enricher(*, model="claude-sonnet-4-6", topic_vocab=None, max_chars=120000,
                  max_tokens=4096, on_usage=None):
    """Build the real enrich_fn(transcript, parsed) -> dict. Needs ANTHROPIC_API_KEY.

    max_chars=120000 (~40k tokens) comfortably covers a full ~60-90 min sermon — the
    old 48k cap silently truncated the conclusion of longer ones (#42 follow-up).
    on_usage(input_tokens, output_tokens), if given, is called after the response so
    the caller can report live cost via cost_of().
    """
    import anthropic  # lazy — keeps the core importable without the SDK
    client = anthropic.Anthropic()
    vocab = (f"Vocabulaire de sujets à privilégier: {', '.join(topic_vocab)}." if topic_vocab else "")

    def enrich(transcript: str, parsed: dict) -> dict:
        prompt = PROMPT.format(vocab=vocab, title=parsed.get("raw_title", ""),
                               transcript=transcript[:max_chars])
        resp = client.messages.create(
            model=model, max_tokens=max_tokens,
            output_config={"format": {"type": "json_schema", "schema": ENRICH_SCHEMA}},
            messages=[{"role": "user", "content": prompt}],
        )
        usage = getattr(resp, "usage", None)
        if on_usage and usage is not None:
            on_usage(usage.input_tokens, usage.output_tokens)
        # The rich schema can run long; a truncated response is invalid JSON. Fail loudly
        # (the runner catches it → resume retries) rather than crash with an opaque error.
        if getattr(resp, "stop_reason", None) == "max_tokens":
            raise RuntimeError(f"enrichment truncated at max_tokens={max_tokens}; raise it")
        import json
        text = next(b.text for b in resp.content if b.type == "text")
        return json.loads(text)

    return enrich
