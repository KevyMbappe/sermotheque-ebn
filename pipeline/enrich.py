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
        "summary": {"type": "string", "description": "2-3 sentence French summary, faithful to the audio."},
        "key_points": {"type": "array", "items": {"type": "string"},
                       "description": "3-6 short bullets tracing the sermon's main movements/arguments."},
        "topics": {"type": "array", "items": {"type": "string"},
                   "description": "3-7 topics; prefer the provided controlled vocabulary."},
        "references": {"type": "array", "items": {"type": "string"},
                       "description": "People/works/confessions actually CITED (e.g. 'Jean Calvin', 'Confession de foi de 1689', 'Augustin'). Confirm, don't invent; empty if none."},
        "questions": {"type": "array", "items": {"type": "string"},
                      "description": "2-4 reflection/discussion questions for a small group (these are study aids — generated, not quoted)."},
        "primary_scripture": {"type": "string", "description": "Main passage preached (e.g. 'Luc 1:26-38'), or empty."},
        "scripture_refs": {"type": "array", "items": {"type": "string"},
                           "description": "Other passages cited in the sermon."},
        "series_hint": {"type": "string", "description": "Series/study context mentioned (e.g. 'Confession de foi ch.8'), or empty."},
    },
    "required": ["description", "summary", "key_points", "topics", "references", "questions",
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
À partir de la TRANSCRIPTION (français, générée automatiquement — ignore les coquilles d'ASR),
renvoie un JSON (tout en français):
- description: UNE phrase accrocheuse (≤30 mots) à afficher sous la vidéo (une accroche, pas un résumé);
- summary: un résumé fidèle de 2-3 phrases;
- key_points: 3-6 points clés retraçant le déroulé de la prédication;
- topics: 3-7 sujets théologiques;
- references: personnes/œuvres/confessions réellement CITÉES (ex: Jean Calvin, Confession de foi de 1689) — n'invente pas, vide si aucune;
- questions: 2-4 questions de réflexion pour un groupe (ce sont des aides générées);
- primary_scripture: le passage principal prêché; scripture_refs: les autres passages cités; series_hint: contexte de série.
Confirme, n'invente pas (sauf les questions, qui sont des aides). {vocab}

Titre (indice): {title}
TRANSCRIPTION:
{transcript}
"""


def make_enricher(*, model="claude-sonnet-4-6", topic_vocab=None, max_chars=120000, on_usage=None):
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
            model=model, max_tokens=1500,
            output_config={"format": {"type": "json_schema", "schema": ENRICH_SCHEMA}},
            messages=[{"role": "user", "content": prompt}],
        )
        usage = getattr(resp, "usage", None)
        if on_usage and usage is not None:
            on_usage(usage.input_tokens, usage.output_tokens)
        import json
        text = next(b.text for b in resp.content if b.type == "text")
        return json.loads(text)

    return enrich
