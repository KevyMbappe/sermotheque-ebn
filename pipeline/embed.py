#!/usr/bin/env python3
"""
Sermothèque EBN — voiceprint adapter (#46): the THIRD injected external step, beside
transcribe + enrich. `make_embedder()` builds `embed(audio_path) -> [float] (256-d)`, a
speaker embedding (Resemblyzer) computed from the sermon's audio.

Why only CAPTURE here, not attribute: the voiceprint is the *one-shot* speaker datum — it
needs the audio, which we download once and delete. Matching a voiceprint to a preacher is
just cosine vs per-speaker centroids on the stored vectors — free and re-runnable anytime —
so attribution lives elsewhere (read voiceprints.json later), and the one-go pass need only
grab the vector while the audio is in hand.

`resemblyzer`/`torch` are lazy-imported so the pure core + the offline tests import without
them; tests inject a fake embedder.
"""


def make_embedder():
    """Build the real embed_fn(audio_path) -> list[float]. Needs `resemblyzer` (+ torch)."""
    from resemblyzer import VoiceEncoder, preprocess_wav   # lazy — keeps the core importable
    encoder = VoiceEncoder()

    def embed(audio_path) -> list:
        return encoder.embed_utterance(preprocess_wav(str(audio_path))).tolist()

    return embed
