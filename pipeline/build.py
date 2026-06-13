#!/usr/bin/env python3
"""
Sermothèque EBN — rebuild the whole catalog in order.
Run: python3 pipeline/build.py   (from anywhere)
"""
import parse_catalog
import cluster_series
import match_youtube

if __name__ == "__main__":
    for step in (parse_catalog, cluster_series, match_youtube):
        print(f"\n=== {step.__name__} ===")
        step.main()
