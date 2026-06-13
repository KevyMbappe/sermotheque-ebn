#!/usr/bin/env python3
"""
Sermothèque EBN — rebuild the whole catalog in order.
Run: python3 pipeline/build.py   (from anywhere)
"""
import parse_catalog
import match_youtube
import fold_orphans
import cluster_series

if __name__ == "__main__":
    # parse SoundCloud → match YouTube → fold orphans into the union → cluster series over all
    for step in (parse_catalog, match_youtube, fold_orphans, cluster_series):
        print(f"\n=== {step.__name__} ===")
        step.main()
