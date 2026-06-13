#!/usr/bin/env python3
"""
Sermothèque EBN — transcription step (one of the two injected, external steps).

Two pieces:
  • clean_transcript(text)  — pure, deterministic, CONSERVATIVE regex fixes for the
                              systematic ASR artifacts of the regular (Lusophone-accented)
                              preacher. Only multi-word, unambiguous patterns — never blanket
                              homophone swaps. Heavily unit-tested.
  • make_transcriber(...)   — builds the real transcribe_fn(source) -> str: download audio to
                              the gitignored cache, run mlx-whisper, clean, delete the audio.
                              Shelled out to the venv binaries so the core stays pure-stdlib and
                              importable without mlx/yt-dlp installed (tests inject a fake instead).
"""
import json
import os
import re
import subprocess
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache"                       # gitignored: downloaded audio + scratch, in-project

# Tools live in the project-local .venv (gitignored), not /tmp. Overridable via env.
_VENV_BIN = ROOT / ".venv" / "bin"
YTDLP = os.environ.get("SERMO_YTDLP", str(_VENV_BIN / "yt-dlp"))
MLX_WHISPER = os.environ.get("SERMO_MLX_WHISPER", str(_VENV_BIN / "mlx_whisper"))
MODEL = "mlx-community/whisper-large-v3-turbo"

# --- conservative ASR cleanup -------------------------------------------------
# Each rule is (pattern, replacement). Patterns are multi-word and unambiguous in this
# corpus, so they don't false-positive on legitimate French ("plusieurs fois", "les dieux
# des nations"). Extend deliberately, with a test per rule.
_CLEAN_RULES = [
    (re.compile(r"\bconfession des? fois\b", re.I), "confession de foi"),
    (re.compile(r"\bla fois chrétienne\b", re.I), "la foi chrétienne"),
    (re.compile(r"\brègle des fois\b", re.I), "règle de foi"),
    (re.compile(r"\bDieu les Pères\b"), "Dieu le Père"),
    (re.compile(r"\bDieu les Fils\b"), "Dieu le Fils"),
    (re.compile(r"\bDieu les Saint-Esprits?\b"), "Dieu le Saint-Esprit"),
    (re.compile(r"\bles Seigneurs Jésus\b"), "le Seigneur Jésus"),
]


def clean_transcript(text: str) -> str:
    for pat, repl in _CLEAN_RULES:
        text = pat.sub(repl, text)
    return text


def _slug(s):
    s = "".join(c for c in unicodedata.normalize("NFD", s.lower())
                if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:60]


def download_audio(url, cache_dir=CACHE, ytdlp=YTDLP):
    """Download a SoundCloud/YouTube URL to mp3 in the cache. Returns the path."""
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    out = cache_dir / f"{_slug(url)}.%(ext)s"
    subprocess.run([ytdlp, "-x", "--audio-format", "mp3", "--no-warnings",
                    "-o", str(out), url], check=True, capture_output=True)
    mp3s = sorted(cache_dir.glob(f"{_slug(url)}.mp3"))
    if not mp3s:
        raise RuntimeError(f"download produced no mp3 for {url}")
    return mp3s[0]


_SIDECAR_EXTS = (".txt", ".vtt", ".srt", ".tsv", ".json")


def asr(audio_path, model=MODEL, mlx_whisper=MLX_WHISPER):
    """Transcribe an audio file with mlx-whisper (French), capturing timestamps.

    Returns a dict: {text, vtt, segments, language}.
      • text     — plain transcript (drives enrichment + search).
      • vtt       — subtitle-ready WebVTT, segment timestamps (→ EN/PT subtitles,
                    audio-synced reading, deep-linking "jump to where he says X").
      • segments  — list of {start, end, text, words[], avg_logprob, no_speech_prob,
                    compression_ratio}; word-level timing enables search-to-moment and
                    karaoke highlight, and per-segment confidence flags shaky stretches
                    for a human pass. Captured here because re-deriving it later means
                    re-running ASR — so we extract the maximum in the one pass (#42).
    """
    audio_path = Path(audio_path)
    stem, out = audio_path.stem, audio_path.parent
    subprocess.run([mlx_whisper, str(audio_path), "--model", model, "--language", "fr",
                    "--output-dir", str(out), "--output-name", stem,
                    "--output-format", "all", "--word-timestamps", "True"],
                   check=True, capture_output=True)
    data = json.loads((out / f"{stem}.json").read_text(encoding="utf-8"))
    return {
        "text": (out / f"{stem}.txt").read_text(encoding="utf-8"),
        "vtt": (out / f"{stem}.vtt").read_text(encoding="utf-8"),
        "segments": data.get("segments", []),
        "language": data.get("language", "fr"),
    }


def make_transcriber(*, keep_audio=False, model=MODEL):
    """Build the real transcribe_fn(source) -> {text, vtt, segments, language}.

    `source` must provide an audio location: either a pre-downloaded `audio_path`,
    or a `url` (SoundCloud permalink / YouTube watch URL) to fetch. The conservative
    ASR cleanup is applied to both the plain text and the VTT cues (the substitution
    rules match French words, never the timestamp lines, so VTT is safe to clean).
    """
    def transcribe(source: dict) -> dict:
        audio = source.get("audio_path")
        downloaded = None
        if not audio:
            url = source.get("url") or source.get("soundcloud_url") or source.get("youtube_url")
            if not url:
                raise ValueError("transcribe: source needs audio_path or a url")
            audio = downloaded = download_audio(url)
        result = asr(audio, model=model)
        result["text"] = clean_transcript(result["text"])
        result["vtt"] = clean_transcript(result["vtt"])
        if downloaded and not keep_audio:
            base = str(Path(downloaded).with_suffix(""))
            for ext in (".mp3", *_SIDECAR_EXTS):
                Path(base + ext).unlink(missing_ok=True)
        return result
    return transcribe
