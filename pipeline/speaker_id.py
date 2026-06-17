#!/usr/bin/env python3
"""
Sermothèque EBN — audio speaker attribution (#49; the deferred half of #46).

The voiceprint pass (#46) captures one 256-float embedding per sermon but nothing READ them:
speaker still came only from the title default-rule (#45), so the CSV shows just `title` /
`default-rule` and known mislabels (the Ézéchiel sermons are Stephan, not David) stand.

This module closes that loop. It is speaker VERIFICATION over a small, known cast (Pastor
David + the elders Stephan, Nathanaël, Loïc, Christian, plus named guests), NOT open-set
diarization. It:
  • builds one centroid per speaker from GROUND-TRUTH voiceprints only — title-confirmed
    speakers + human overrides (never the unverified default-rule, which would poison David's
    centroid with the very mislabels we want to catch);
  • classifies every sermon's voiceprint by cosine similarity to the nearest centroid;
  • assigns a speaker + provenance via the ladder (#45): human > audio-fingerprint > title >
    default-rule. `audio-fingerprint` is set only on a CONFIDENT match (similarity ≥ accept
    floor AND a clear margin over the runner-up); otherwise the structural label stands.

Re-runnable from the stored vectors at no audio cost — so it is its own store + writeback,
not part of the one-shot capture. Pure stdlib (the embeddings are already floats on disk).
"""
import json
import math
from pathlib import Path

import voiceprint_store

ROOT = Path(__file__).resolve().parent.parent
CAT = ROOT / "data" / "catalog" / "catalog.json"
STORE = ROOT / "data" / "catalog" / "speakers.json"          # this module's output (attribution)
OVERRIDES = ROOT / "data" / "catalog" / "speaker_overrides.json"  # human-confirmed: {id: speaker}

# Decision thresholds (cosine over unit-normalized Resemblyzer embeddings). CALIBRATED from the
# leave-one-out report on our own labels: same-speaker cosine ≥ 0.94, cross-speaker ≤ 0.89 —
# a clean gap. The accept floor sits IN that gap so only same-speaker-grade matches auto-apply;
# matches in the overlap zone (e.g. a sermon vs a thin 2-example centroid in different audio
# conditions) fall to "ambiguous" and are surfaced as candidates, not written.
SIM_ACCEPT = 0.90     # minimum similarity to the nearest centroid to trust an audio match
MARGIN_MIN = 0.03     # nearest must beat the runner-up by at least this (else "ambiguous")
CANDIDATE_FLOOR = 0.80   # ambiguous matches above this are worth surfacing for human review


# ----- vector math (unit-normalized embeddings, cosine) ---------------------------------------

def _unit(v):
    n = math.sqrt(sum(x * x for x in v)) or 1e-9
    return [x / n for x in v]


def cosine(a, b):
    """Cosine similarity of two raw vectors."""
    na = math.sqrt(sum(x * x for x in a)) or 1e-9
    nb = math.sqrt(sum(x * x for x in b)) or 1e-9
    return sum(x * y for x, y in zip(a, b)) / (na * nb)


def centroid(vectors):
    """Mean of unit-normalized vectors (then re-normalized) — the speaker's voice prototype."""
    units = [_unit(v) for v in vectors]
    dim = len(units[0])
    mean = [sum(u[i] for u in units) / len(units) for i in range(dim)]
    return _unit(mean)


MIN_EXAMPLES = 2      # a centroid from a single sermon is too thin to auto-apply (→ "review")


def build_centroids(labeled):
    """{speaker: [(id, vec), …]} → {speaker: centroid_vec}. One example still forms a centroid."""
    return {spk: centroid([v for _, v in items]) for spk, items in labeled.items() if items}


def classify(vec, centroids):
    """Nearest centroid by cosine → (speaker, sim, margin_to_2nd). margin=inf if only one centroid."""
    ranked = sorted(((cosine(vec, c), spk) for spk, c in centroids.items()), reverse=True)
    sim, spk = ranked[0]
    margin = (sim - ranked[1][0]) if len(ranked) > 1 else float("inf")
    return spk, sim, margin


def is_confident(sim, margin):
    return sim >= SIM_ACCEPT and margin >= MARGIN_MIN


# ----- attribution over the whole catalog ------------------------------------------------------

def ground_truth(rows, voiceprints, overrides):
    """{speaker: [(id, vec)]} from RELIABLE labels only: human overrides + title-provenance.
    Default-rule labels are excluded on purpose — they're the unverified guesses under test."""
    by_id = {r["id"]: r for r in rows}
    labeled = {}
    for vid, vp in voiceprints.items():
        vec = vp.get("embedding")
        if not vec:
            continue
        spk = overrides.get(vid) or (by_id.get(vid, {}).get("speaker")
                                     if by_id.get(vid, {}).get("speaker_provenance") == "title" else None)
        if spk:
            labeled.setdefault(spk, []).append((vid, vec))
    return labeled


def attribute(rows, voiceprints, overrides):
    """Classify every sermon that has a voiceprint. Returns a list of attribution records:
    {id, current_speaker, current_provenance, predicted, sim, margin, runner_up, n_examples,
     decision}.

    decision (what the report shows / what gets applied):
      • human         — a human override exists (applied, wins everything)
      • confirm       — audio agrees with the current label (applied: upgrades default-rule)
      • reassign      — audio overrides a default-rule/blank guess (applied)
      • title-conflict— audio disagrees with an explicit TITLE label (NOT applied — title wins,
                        but surfaced for human review)
      • review        — match is to a thin centroid (<MIN_EXAMPLES) (NOT applied — too few examples)
      • ambiguous     — below the similarity/margin floor (NOT applied)
      • no-centroid   — no ground truth at all
    """
    by_id = {r["id"]: r for r in rows}
    gt = ground_truth(rows, voiceprints, overrides)
    counts = {spk: len(items) for spk, items in gt.items()}
    centroids = build_centroids(gt)
    out = []
    for vid, vp in sorted(voiceprints.items()):
        vec = vp.get("embedding")
        if not vec:
            continue
        cur = by_id.get(vid, {})
        cur_spk, cur_prov = cur.get("speaker"), cur.get("speaker_provenance")
        rec = {"id": vid, "current_speaker": cur_spk, "current_provenance": cur_prov,
               "predicted": None, "sim": None, "margin": None, "runner_up": None, "n_examples": None}
        if vid in overrides:
            rec.update(predicted=overrides[vid], decision="human")
            out.append(rec); continue
        if not centroids:
            rec["decision"] = "no-centroid"; out.append(rec); continue
        # classify against centroids built from OTHER sermons (exclude self if it's ground truth)
        cents = centroids
        if any(vid == i for items in gt.values() for i, _ in items):
            held = {spk: [(i, v) for i, v in items if i != vid] for spk, items in gt.items()}
            cents = build_centroids({s: it for s, it in held.items() if it})
        spk, sim, margin = classify(vec, cents)
        runner = sorted(((cosine(vec, c), s) for s, c in cents.items()), reverse=True)
        rec.update(predicted=spk, sim=round(sim, 4), margin=round(margin, 4),
                   runner_up=(runner[1][1] if len(runner) > 1 else None), n_examples=counts.get(spk))
        if not is_confident(sim, margin):
            rec["decision"] = "ambiguous"
        elif counts.get(spk, 0) < MIN_EXAMPLES:
            rec["decision"] = "review"               # centroid too thin to trust automatically
        elif spk == cur_spk:
            rec["decision"] = "confirm"
        elif cur_prov == "title":
            rec["decision"] = "title-conflict"       # don't override an explicit title; flag it
        else:
            rec["decision"] = "reassign"
        out.append(rec)
    return out


def to_store(records):
    """Attribution records → id-keyed store of the rows that yield a usable label."""
    store = {}
    for r in records:
        if r["decision"] == "human":
            store[r["id"]] = {"speaker": r["predicted"], "provenance": "human"}
        elif r["decision"] in ("confirm", "reassign"):
            store[r["id"]] = {"speaker": r["predicted"], "provenance": "audio-fingerprint",
                              "confidence": r["sim"], "runner_up": r["runner_up"]}
        # ambiguous / no-centroid → no audio label; the structural speaker stands
    return store


def save_store(records, path=STORE):
    store = to_store(records)
    Path(path).write_text(json.dumps(store, ensure_ascii=False, indent=2, sort_keys=True),
                          encoding="utf-8")
    return store


# ----- writeback: apply onto the catalog (respecting the ladder) -------------------------------

# Provenance ladder (#45): human > title > audio-fingerprint > default-rule. The church's own
# title labels outrank an audio guess — audio's job is to fix the unverified default-rule/blank,
# and to FLAG (not silently override) disagreements with a title.
_RANK = {"human": 4, "title": 3, "audio-fingerprint": 2, "default-rule": 1, None: 0}


def apply(rows, store):
    """Layer the speaker store onto catalog rows by id, only when it outranks the current
    provenance. Returns (rows, changed_count)."""
    changed = 0
    for r in rows:
        rec = store.get(r.get("id"))
        if not rec:
            continue
        if _RANK[rec["provenance"]] > _RANK.get(r.get("speaker_provenance")):
            if r.get("speaker") != rec["speaker"] or r.get("speaker_provenance") != rec["provenance"]:
                changed += 1
            r["speaker"] = rec["speaker"]
            r["speaker_provenance"] = rec["provenance"]
    return rows, changed


def writeback(catalog_path=CAT, store_path=STORE):
    rows = json.loads(Path(catalog_path).read_text(encoding="utf-8"))
    store = json.loads(Path(store_path).read_text(encoding="utf-8")) if Path(store_path).exists() else {}
    rows, changed = apply(rows, store)
    Path(catalog_path).write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    from cluster_series import write_csv
    write_csv(rows)
    return changed


def _load_overrides(path=OVERRIDES):
    return json.loads(Path(path).read_text(encoding="utf-8")) if Path(path).exists() else {}


def main():
    import argparse
    import collections
    ap = argparse.ArgumentParser(description="Audio speaker attribution from captured voiceprints (#49).")
    ap.add_argument("--write", action="store_true", help="write speakers.json (else dry-run report only)")
    ap.add_argument("--writeback", action="store_true", help="also apply onto catalog.json + csv")
    args = ap.parse_args()

    rows = json.loads(CAT.read_text(encoding="utf-8"))
    vps = voiceprint_store.load()
    overrides = _load_overrides()
    gt = ground_truth(rows, vps, overrides)

    print(f"voiceprints: {len(vps)} | ground-truth speakers (title + human): {len(gt)}")
    for spk, items in sorted(gt.items(), key=lambda kv: -len(kv[1])):
        print(f"   {spk:22} {len(items)} example(s)")

    # Leave-one-out over ground truth → accuracy + similarity calibration.
    correct = total = 0
    same_sims, cross_sims = [], []
    for spk, items in gt.items():
        for vid, vec in items:
            held = {s: [(i, v) for i, v in it if i != vid] for s, it in gt.items()}
            cents = build_centroids({s: it for s, it in held.items() if it})
            if spk not in cents:
                continue   # only one example → can't LOO
            pred, sim, _ = classify(vec, cents)
            total += 1; correct += (pred == spk)
            for s, c in cents.items():
                (same_sims if s == spk else cross_sims).append(cosine(vec, c))
    if total:
        print(f"\nleave-one-out (speakers with ≥2 examples): {correct}/{total} correct")
    if same_sims and cross_sims:
        print(f"  same-speaker cosine : min {min(same_sims):.3f}  mean {sum(same_sims)/len(same_sims):.3f}")
        print(f"  cross-speaker cosine: max {max(cross_sims):.3f}  mean {sum(cross_sims)/len(cross_sims):.3f}")
        print(f"  (accept floor {SIM_ACCEPT}, margin {MARGIN_MIN})")

    records = attribute(rows, vps, overrides)
    dec = collections.Counter(r["decision"] for r in records)
    print(f"\nattribution over {len(records)} voiceprints: {dict(dec)}")

    def show(decision, header):
        rs = [r for r in records if r["decision"] == decision]
        if rs:
            print(f"\n{header} ({len(rs)}):")
            for r in sorted(rs, key=lambda r: -(r["sim"] or 0)):
                s = f"sim {r['sim']:.3f} margin {r['margin']:.3f}" if r["sim"] else ""
                print(f"   {r['id']:16} {str(r['current_speaker']):16} → {str(r['predicted']):16} {s}")

    show("reassign", "✦ APPLIED — audio corrects a default-rule/blank guess")
    show("title-conflict", "⚑ REVIEW — audio disagrees with an explicit TITLE (title kept)")
    show("review", "? REVIEW — match is to a thin (<2 example) centroid (not applied)")
    cand = [r for r in records if r["decision"] == "ambiguous" and (r["sim"] or 0) >= CANDIDATE_FLOOR]
    if cand:
        print(f"\n· CANDIDATES — plausible but below the confident floor {SIM_ACCEPT} (not applied) ({len(cand)}):")
        for r in sorted(cand, key=lambda r: -(r["sim"] or 0)):
            print(f"   {r['id']:16} {str(r['current_speaker']):16} ~ {str(r['predicted']):16}"
                  f" sim {r['sim']:.3f} margin {r['margin']:.3f}")

    if args.write:
        store = save_store(records)
        print(f"\nwrote {STORE.name}: {len(store)} audio/human labels")
    if args.writeback:
        n = writeback()
        print(f"applied onto catalog: {n} rows changed")


if __name__ == "__main__":
    main()
