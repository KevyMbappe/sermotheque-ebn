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
import re
import subprocess
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache"

# Defaults are overridable (production installs these on PATH).
YTDLP = "/tmp/ytdlp-venv/bin/yt-dlp"
MLX_WHISPER = "/tmp/asr-venv/bin/mlx_whisper"
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


def asr(audio_path, model=MODEL, mlx_whisper=MLX_WHISPER):
    """Transcribe an audio file with mlx-whisper (French). Returns raw text."""
    audio_path = Path(audio_path)
    subprocess.run([mlx_whisper, str(audio_path), "--model", model, "--language", "fr",
                    "--output-dir", str(audio_path.parent),
                    "--output-name", audio_path.stem, "--output-format", "txt"],
                   check=True, capture_output=True)
    return (audio_path.parent / f"{audio_path.stem}.txt").read_text(encoding="utf-8")


def make_transcriber(*, keep_audio=False, model=MODEL):
    """Build the real transcribe_fn(source) -> cleaned transcript text.

    `source` must provide an audio location: either a pre-downloaded `audio_path`,
    or a `url` (SoundCloud permalink / YouTube watch URL) to fetch.
    """
    def transcribe(source: dict) -> str:
        audio = source.get("audio_path")
        downloaded = None
        if not audio:
            url = source.get("url") or source.get("soundcloud_url") or source.get("youtube_url")
            if not url:
                raise ValueError("transcribe: source needs audio_path or a url")
            audio = downloaded = download_audio(url)
        raw = asr(audio, model=model)
        if downloaded and not keep_audio:
            Path(downloaded).unlink(missing_ok=True)
            Path(downloaded).with_suffix(".txt").unlink(missing_ok=True)
        return clean_transcript(raw)
    return transcribe
