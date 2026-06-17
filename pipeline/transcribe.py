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
import sys
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


# --- content-based language detection (decision #48) ---------------------------
# Whisper's 30-second language guess is unreliable on our corpus: a French intro on an
# English talk → "fr" → garbage; a French sermon opening with "Thank you" → "en". The
# transcript TEXT itself is the reliable signal — thousands of words of distinctive
# function words. This decides the catalog `language` label (not the ASR detector).
_FR_WORDS = frozenset("le la les de des du un une et est que qui dans pour pas plus nous "
                      "vous ce cette il elle son sa ses mais avec sur par ne au aux on "
                      "comme tout être avoir fait dieu".split())
_EN_WORDS = frozenset("the of and to a in is that it was for on are with as his they be at "
                      "this have from not but by you we god he which will all would there".split())


def detect_language(text: str) -> str | None:
    """'fr' / 'en' from function-word frequency over the transcript, or None if unclear
    (too little text, or no decisive margin). Robust on long transcripts; ignores ASR
    artifacts. Used to set the catalog language label from the audio's actual content."""
    words = re.findall(r"[a-zà-ÿ]+", text.lower())
    if len(words) < 30:
        return None
    fr = sum(w in _FR_WORDS for w in words)
    en = sum(w in _EN_WORDS for w in words)
    if max(fr, en) == 0:
        return None
    return "fr" if fr >= en * 1.3 else "en" if en >= fr * 1.3 else None


def _looks_garbage(text: str) -> bool:
    """True when ASR produced near-empty output (wrong language on speech, or non-speech):
    real characters collapse to a tiny fraction of the transcript. A correct transcript
    sits ~0.75-0.85; a forced-wrong-language one (e.g. English audio decoded as French)
    is ~0.01 ('...!\\n' repeated). Threshold 0.3 separates them with wide margin."""
    if not text:
        return True
    real = re.sub(r"[\s.!?¿¡…]+", "", text)
    return len(real) / len(text) < 0.3


def count_artifacts(text: str) -> int:
    """How many systematic ASR artifacts (the _CLEAN_RULES patterns) appear in the text.
    A lusophone/non-native accent inflates this — a speaker signal in the raw transcript (#46)."""
    return sum(len(pat.findall(text)) for pat, _ in _CLEAN_RULES)


def _slug(s):
    s = "".join(c for c in unicodedata.normalize("NFD", s.lower())
                if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:60]


# Generous ceilings so a *hung* yt-dlp/mlx can't wedge an unattended multi-hour run
# (a real download/transcription finishes well under these); on timeout the subprocess
# raises TimeoutExpired → build_entry propagates → the runner logs FAILED and resumes it.
DL_TIMEOUT = 900      # 15 min — a download should take seconds–minutes
ASR_TIMEOUT = 2400    # 40 min — ASR is ~13× real-time, so even a 90-min sermon is ~7 min


def _run(cmd, verbose, timeout=None):
    """Run a subprocess. When verbose, the tool's progress is shown on stderr (its
    stdout is redirected there too) so our own stdout stays clean for the entry JSON;
    otherwise it's captured/silent (the default — keeps tests and library use quiet)."""
    if verbose:
        subprocess.run(cmd, check=True, stdout=sys.stderr, timeout=timeout)
    else:
        subprocess.run(cmd, check=True, capture_output=True, timeout=timeout)


def probe_metadata(url, ytdlp=YTDLP):
    """Fetch title / upload_date / duration without downloading (one fast yt-dlp call)."""
    res = subprocess.run(
        [ytdlp, "--skip-download", "--no-warnings",
         "--print", "%(title)s\t%(upload_date)s\t%(duration)s", url],
        check=True, capture_output=True, text=True)
    title, date, dur = (res.stdout.strip().split("\t") + ["", "", ""])[:3]
    return {"title": title or None, "upload_date": date or None,
            "duration": int(float(dur)) if dur else None}


DL_RETRIES = 3        # YouTube throttles with transient HTTP 403s; a short backoff clears them
DL_BACKOFF = 10       # seconds, multiplied by the attempt number (10s, 20s, …)


def download_audio(url, cache_dir=CACHE, ytdlp=YTDLP, verbose=False, retries=DL_RETRIES):
    """Download a SoundCloud/YouTube URL to mp3 in the cache. Returns the path.

    Retries with linear backoff (decision #48): YouTube intermittently answers downloads
    with HTTP 403 (anti-bot throttling) — in the 30-sermon batch 3/12 YT videos hit it and
    every one succeeded on a plain retry. SoundCloud has not shown this. Retrying here (not
    just at the runner level) means a 403 costs seconds, not a re-queued sermon."""
    import time
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    out = cache_dir / f"{_slug(url)}.%(ext)s"
    cmd = [ytdlp, "-x", "--audio-format", "mp3", "--no-warnings", "-o", str(out), url]
    last = None
    for attempt in range(1, retries + 1):
        try:
            _run(cmd, verbose, DL_TIMEOUT)
            break
        except subprocess.CalledProcessError as e:   # transient (403/network); retry with backoff
            last = e
            if attempt == retries:
                raise
            wait = DL_BACKOFF * attempt
            print(f"  download attempt {attempt}/{retries} failed ({url}); retrying in {wait}s",
                  file=sys.stderr, flush=True)
            time.sleep(wait)
    mp3s = sorted(cache_dir.glob(f"{_slug(url)}.mp3"))
    if not mp3s:
        raise RuntimeError(f"download produced no mp3 for {url}" + (f" (last error: {last})" if last else ""))
    return mp3s[0]


_SIDECAR_EXTS = (".txt", ".vtt", ".srt", ".tsv", ".json")


def asr(audio_path, model=MODEL, mlx_whisper=MLX_WHISPER, word_timestamps=False, verbose=False,
        language=None):
    """Transcribe an audio file with mlx-whisper. Returns {text, vtt, segments, language}.
      • text      — plain transcript (drives enrichment + search).
      • vtt       — subtitle-ready WebVTT, segment timestamps (→ EN/PT subtitles,
                    audio-synced reading, deep-linking). Persisted by default.
      • segments  — segment-level {start, end, text, avg_logprob, no_speech_prob, …},
                    free. With word_timestamps=True each segment also gets per-word
                    timing (`words[]`) — heavier; opt-in (see #42). Not persisted unless
                    build_entry(persist_segments=True).

    `language` pins the ASR language; **None (default) auto-detects** (decision #48).
    We used to force French — but the catalog `language` is title-derived and unreliable
    (English titles on French sermons, and vice-versa), so forcing fr turned genuinely
    English audio into a transcript of pure '...'. Auto-detect reads the audio truth; the
    detected language flows back into the entry and overrides the title guess.
    """
    audio_path = Path(audio_path)
    stem, out = audio_path.stem, audio_path.parent
    # Clear any prior sidecars for this stem first: mlx-whisper skips regenerating when its
    # output already exists, so a retry in a different language would otherwise read back the
    # stale transcript (the #48 fr→en retry silently kept the garbage). Guarantees a fresh run.
    for ext in _SIDECAR_EXTS:
        (out / f"{stem}{ext}").unlink(missing_ok=True)
    cmd = [mlx_whisper, str(audio_path), "--model", model,
           "--output-dir", str(out), "--output-name", stem,
           "--output-format", "all", "--word-timestamps", "True" if word_timestamps else "False",
           "--verbose", "False"]    # progress bar, not a live segment dump
    if language:                    # else mlx-whisper auto-detects from the audio
        cmd += ["--language", language]
    _run(cmd, verbose, ASR_TIMEOUT)
    data = json.loads((out / f"{stem}.json").read_text(encoding="utf-8"))
    return {
        "text": (out / f"{stem}.txt").read_text(encoding="utf-8"),
        "vtt": (out / f"{stem}.vtt").read_text(encoding="utf-8"),
        "segments": data.get("segments", []),
        "language": data.get("language") or language,
    }


def make_transcriber(*, keep_audio=False, model=MODEL, word_timestamps=False, verbose=False,
                     embed=None, language=None):
    """Build the real transcribe_fn(source) -> {text, vtt, segments, language}.

    `source` must provide an audio location: either a pre-downloaded `audio_path`,
    or a `url` (SoundCloud permalink / YouTube watch URL) to fetch. The conservative
    ASR cleanup is applied to both the plain text and the VTT cues (the substitution
    rules match French words, never the timestamp lines, so VTT is safe to clean).
    `verbose` streams yt-dlp/whisper progress to stderr; `word_timestamps` opts into
    the heavier per-word timing (only worth it if persisting segments). `embed`, if given,
    captures a voiceprint from the SAME download (before the audio is deleted, #46).
    """
    def transcribe(source: dict) -> dict:
        audio = source.get("audio_path")
        downloaded = None
        if not audio:
            url = source.get("url") or source.get("soundcloud_url") or source.get("youtube_url")
            if not url:
                raise ValueError("transcribe: source needs audio_path or a url")
            audio = downloaded = download_audio(url, verbose=verbose)
        # Default to French (the corpus is FR-dominant and forcing fr is proven on the 489
        # SC sermons); auto-detect is unreliable here (#48). If that yields garbage — genuinely
        # English audio decoded as French collapses to '...' — retry once forcing English.
        primary = language or "fr"
        result = asr(audio, model=model, word_timestamps=word_timestamps, verbose=verbose,
                     language=primary)
        if language is None and _looks_garbage(result["text"]):
            alt = "en" if primary == "fr" else "fr"
            print(f"  transcript looks empty under '{primary}'; retrying as '{alt}'",
                  file=sys.stderr, flush=True)
            result = asr(audio, model=model, word_timestamps=word_timestamps, verbose=verbose,
                         language=alt)
        result["text_raw"] = result["text"]          # uncleaned ASR — preserves the accent signature (#45)
        result["text"] = clean_transcript(result["text"])
        result["vtt"] = clean_transcript(result["vtt"])
        # Label from the transcript CONTENT, not Whisper's 30s guess (#48); fall back to ASR's.
        result["language"] = detect_language(result["text"]) or result.get("language") or primary
        if embed:                                    # voiceprint from the same audio (#46)
            try:
                result["embedding"] = embed(audio)
            except Exception as e:                   # never let an embed failure cost us the transcript
                print(f"  voiceprint failed (kept transcript): {e!r}", file=sys.stderr)
                result["embedding"] = None
        if downloaded and not keep_audio:
            base = str(Path(downloaded).with_suffix(""))
            for ext in (".mp3", *_SIDECAR_EXTS):
                Path(base + ext).unlink(missing_ok=True)
        return result
    return transcribe
