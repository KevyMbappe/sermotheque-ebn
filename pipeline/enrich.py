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
        "summary": {"type": "string", "description": "2-3 sentence French summary, faithful to the audio."},
        "topics": {"type": "array", "items": {"type": "string"},
                   "description": "3-7 topics; prefer the provided controlled vocabulary."},
        "primary_scripture": {"type": "string", "description": "Main passage preached (e.g. 'Luc 1:26-38'), or empty."},
        "scripture_refs": {"type": "array", "items": {"type": "string"},
                           "description": "Other passages cited in the sermon."},
        "series_hint": {"type": "string", "description": "Series/study context mentioned (e.g. 'Confession de foi ch.8'), or empty."},
    },
    "required": ["summary", "topics", "primary_scripture", "scripture_refs", "series_hint"],
    "additionalProperties": False,
}

PROMPT = """Tu enrichis le catalogue de prédications d'une église réformée baptiste francophone.
À partir de la TRANSCRIPTION (français, générée automatiquement — ignore les coquilles d'ASR),
renvoie un JSON: un résumé français de 2-3 phrases fidèle au contenu, 3-7 sujets théologiques,
le passage biblique principal prêché, les autres références citées, et tout contexte de série
mentionné. Confirme, n'invente pas. {vocab}

Titre (indice): {title}
TRANSCRIPTION:
{transcript}
"""


def make_enricher(*, model="claude-sonnet-4-6", topic_vocab=None, max_chars=48000):
    """Build the real enrich_fn(transcript, parsed) -> dict. Needs ANTHROPIC_API_KEY."""
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
        import json
        text = next(b.text for b in resp.content if b.type == "text")
        return json.loads(text)

    return enrich
