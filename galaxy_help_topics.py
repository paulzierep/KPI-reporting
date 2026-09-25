#!/usr/bin/env python3
"""Fetch all topics from the 'usegalaxy.eu support' category on the Galaxy Help forum.

Source: https://help.galaxyproject.org (Discourse)

The usegalaxy.eu support category is a Discourse category. This script pages
through its topic list via the public JSON API and stores the topics (public
forum content) plus per-year counts.

Usage
-----
    python3 galaxy_help_topics.py          # all topics, prints yearly counts
    python3 galaxy_help_topics.py 2024     # counts for one year
"""

import csv
import json
import sys
import urllib.request
from collections import Counter
from pathlib import Path

BASE = "https://help.galaxyproject.org/c/usegalaxy-eu-support/6.json"


def fetch_all_topics():
    topics = []
    page = 1
    while True:
        url = f"{BASE}?page={page}"
        with urllib.request.urlopen(url, timeout=120) as resp:
            data = json.load(resp)
        batch = data["topic_list"]["topics"]
        topics.extend(batch)
        print(f"  page {page}: {len(batch)} (running {len(topics)})")
        if len(batch) < 30:
            break
        page += 1
    return topics


def main():
    years = [int(a) for a in sys.argv[1:] if a.isdigit()] or (2023, 2024, 2025)
    print(f"fetching topics from usegalaxy.eu support category ...")
    topics = fetch_all_topics()

    out = Path(__file__).resolve().parent / "data" / "galaxy_help_usegalaxy_eu_topics.csv"
    out.parent.mkdir(exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            ["topic_id", "created_date", "title", "posts_count", "reply_count",
             "last_post_date"]
        )
        for t in topics:
            writer.writerow(
                [
                    t["id"],
                    t["created_at"][:10],
                    t["title"],
                    t["posts_count"],
                    t["reply_count"],
                    (t.get("last_posted_at") or "")[:10],
                ]
            )
    print(f"wrote {out} ({len(topics)} topics)")

    per_year = Counter(t["created_at"][:4] for t in topics)
    rows = []
    for y in years:
        rows.append((y, per_year.get(str(y), 0)))
        print(f"usegalaxy.eu support topics {y}: {per_year.get(str(y), 0):,}")

    ypath = out.parent / "galaxy_help_usegalaxy_eu_topics_by_year.tsv"
    with open(ypath, "w", encoding="utf-8") as fh:
        fh.write("year\ttopics\n")
        for y, n in sorted(rows):
            fh.write(f"{y}\t{n}\n")
    print(f"wrote {ypath}")


if __name__ == "__main__":
    main()