#!/usr/bin/env python3
"""
Sermothèque EBN — Tier-A text "sermon fingerprint" + nearest-centroid speaker attribution (#46).

A fingerprint is a small feature vector per sermon, from text we already have (no audio model):
  • function-word frequencies  — classic stylometry (Burrows), topic-neutral author signal
  • accent-artifact rate         — clean_transcript matches per 1k words in the RAW transcript;
                                   a non-native accent (David's lusophone) spikes it
  • cadence                      — words per second, from the VTT timestamps
  • vocabulary richness (TTR)
Speakers are named by humans; we build one centroid per named speaker from labeled sermons and
classify the rest by nearest centroid (with a distance threshold → "unknown"). Pure stdlib.

This is Tier A — free, great at David-vs-not-David. Separating the native-French elders from each
other may need Tier B (audio embeddings); `main()` runs a leave-one-out eval to find out.
"""
import json
import math
import re
import statistics as st
from pathlib import Path

from transcribe import count_artifacts

ROOT = Path(__file__).resolve().parent.parent

# High-frequency, topic-neutral French function words (the stylometric backbone).
FUNCTION_WORDS = ("le la les un une de des du et ou mais donc car que qui ne pas plus très bien "
                  "alors aussi comme parce puisque ainsi dans par pour sur avec sans ce cette ces "
                  "il elle ils nous vous je on se y en au aux est sont a ont ce qu d l c n").split()


def _tokens(text):
    return re.findall(r"[a-zàâäéèêëîïôöùûüç']+", text.lower())


def _vtt_seconds(vtt):
    """Total spoken duration from the last VTT timestamp (for cadence)."""
    ts = re.findall(r"(\d{2}):(\d{2})[:.](\d{2})", vtt or "")
    if not ts:
        return None
    h, m, s = ts[-1]
    return int(h) * 3600 + int(m) * 60 + int(s)


def extract(text, raw=None, vtt=None):
    """Raw (un-normalized) fingerprint features for one sermon."""
    w = _tokens(text)
    n = len(w) or 1
    from collections import Counter
    c = Counter(w)
    feats = {f"fw:{f}": c.get(f, 0) / n for f in FUNCTION_WORDS}
    feats["ttr"] = len(set(w[:3000])) / min(n, 3000)
    feats["artifact_per_1k"] = (count_artifacts(raw) / n * 1000) if raw else None
    secs = _vtt_seconds(vtt)
    feats["words_per_sec"] = (n / secs) if secs else None
    return feats


# ----- nearest-centroid model over z-normalized features --------------------------------------

def _matrix(fps):
    """List of feature dicts → (z-normalized rows, feature names). Missing values impute to mean (z=0)."""
    names = sorted({k for fp in fps for k in fp})
    cols = {nm: [fp.get(nm) for fp in fps] for nm in names}
    stats = {}
    for nm, vals in cols.items():
        present = [v for v in vals if v is not None]
        m = st.mean(present) if present else 0.0
        sd = (st.pstdev(present) if len(present) > 1 else 0.0) or 1e-9
        stats[nm] = (m, sd)
    rows = [[((fp.get(nm) if fp.get(nm) is not None else stats[nm][0]) - stats[nm][0]) / stats[nm][1]
             for nm in names] for fp in fps]
    return rows, names


def _centroids(rows, labels):
    by = {}
    for r, lab in zip(rows, labels):
        by.setdefault(lab, []).append(r)
    return {lab: [st.mean(col) for col in zip(*rs)] for lab, rs in by.items()}


def _dist(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def classify(row, centroids):
    """Nearest centroid → (label, distance, margin-to-2nd). Caller applies an 'unknown' threshold."""
    ranked = sorted(((_dist(row, c), lab) for lab, c in centroids.items()))
    (d1, lab), = ranked[:1]
    margin = (ranked[1][0] - d1) if len(ranked) > 1 else float("inf")
    return lab, d1, margin


def leave_one_out(rows, labels):
    """For each labeled row, build centroids from the others and classify it. Returns predictions."""
    preds = []
    for i in range(len(rows)):
        others = [(r, l) for j, (r, l) in enumerate(zip(rows, labels)) if j != i]
        cents = _centroids([r for r, _ in others], [l for _, l in others])
        if labels[i] not in cents:          # only one example of this speaker — can't LOO it
            preds.append((None, None, None)); continue
        preds.append(classify(rows[i], cents))
    return preds


def main():
    import argparse
    import collections
    ap = argparse.ArgumentParser(description="Tier-A text fingerprint — leave-one-out speaker eval.")
    ap.add_argument("--dir", required=True, help="dir of <id>.txt (+ .raw.txt, .vtt)")
    ap.add_argument("--labels", required=True, help="JSON list of {id, speaker}")
    args = ap.parse_args()
    d = Path(args.dir)
    labeled = json.loads(Path(args.labels).read_text())

    fps, labels, ids = [], [], []
    for p in labeled:
        txt = d / f"{p['id']}.txt"
        if not txt.exists():
            continue
        raw = d / f"{p['id']}.raw.txt"
        vtt = d / f"{p['id']}.vtt"
        fps.append(extract(txt.read_text(encoding="utf-8"),
                           raw.read_text(encoding="utf-8") if raw.exists() else None,
                           vtt.read_text(encoding="utf-8") if vtt.exists() else None))
        labels.append(p["speaker"]); ids.append(p["id"])

    print(f"fingerprinted {len(fps)} sermons across {len(set(labels))} speakers\n")
    print(f"{'id':16}{'speaker':16}{'artifact/1k':>12}{'words/sec':>11}")
    for fp, lab, i in zip(fps, labels, ids):
        a = fp.get("artifact_per_1k"); wps = fp.get("words_per_sec")
        print(f"{i:16}{lab[:15]:16}{(f'{a:.1f}' if a is not None else '—'):>12}{(f'{wps:.2f}' if wps else '—'):>11}")

    rows, _ = _matrix(fps)
    preds = leave_one_out(rows, labels)
    scored = [(labels[i], preds[i][0]) for i in range(len(labels)) if preds[i][0] is not None]
    correct = sum(t == p for t, p in scored)
    print(f"\nleave-one-out (speakers with ≥2 examples): {correct}/{len(scored)} correct")
    conf = collections.Counter((t, p) for t, p in scored)
    for (t, p), k in sorted(conf.items()):
        mark = "✓" if t == p else "✗"
        print(f"  {mark} {t} → {p}: {k}")


if __name__ == "__main__":
    main()
