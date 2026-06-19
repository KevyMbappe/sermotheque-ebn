#!/usr/bin/env python3
"""
Sermothèque EBN — rebuild the whole catalog in order.
Run: python3 pipeline/build.py   (from anywhere)
"""
import parse_catalog
import match_youtube
import fold_orphans
import cluster_series
import enrichment_store
import speaker_id

if __name__ == "__main__":
    # parse SoundCloud → match YouTube → fold orphans into the union → cluster series over all
    # → write back enrichment (topics/summary/transcripts survive a rebuild, #44)
    for step in (parse_catalog, match_youtube, fold_orphans, cluster_series, enrichment_store):
        print(f"\n=== {step.__name__} ===")
        step.main()
    # → apply the audio speaker attribution LAST (so the rebuilt catalog keeps audio-fingerprint
    #   labels instead of reverting to the default-rule, #51/#52; regenerates the CSV too)
    print("\n=== speaker_id (writeback) ===")
    changed = speaker_id.writeback()
    print(f"  speaker attribution applied onto {changed} catalog rows")
