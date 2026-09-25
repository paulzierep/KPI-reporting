#!/usr/bin/env python3
"""GTN content stats per year from the training.galaxyproject.org archive.

The Galaxy Training Network periodically freezes a snapshot of the whole site
under https://training.galaxyproject.org/archive/<YYYY-MM-DD>/. Each snapshot
ships a rendered stats page, but only for snapshots from 2023-06 onwards
(2023-01-01 and earlier do not have one). The year-start snapshots
2024-01-01 / 2025-01-01 / 2026-01-01 therefore serve as exact year
boundaries:

    end of 2023  = archive/2024-01-01/stats/
    end of 2024  = archive/2025-01-01/stats/
    end of 2025  = archive/2026-01-01/stats/

so 2024 and 2025 year-over-year growth is exact. 2023 has no baseline
(no 2023-01-01 stats page). The live site header is appended as "current".

Usage
-----
    python3 gtn_archive_stats.py

Writes to `data/`:
  gtn_archive_stats.tsv          absolute counts at each year boundary
  gtn_archive_new_per_year.tsv   year-over-year growth (where a baseline exists)
"""

import re
import urllib.request
from pathlib import Path

END_SNAPSHOTS = {   # end of calendar year -> boundary snapshot
    "2023": "2024-01-01",
    "2024": "2025-01-01",
    "2025": "2026-01-01",
}
START_SNAPSHOTS = {  # start of calendar year -> boundary snapshot (missing = None)
    "2023": None,
    "2024": "2024-01-01",
    "2025": "2025-01-01",
}
CURRENT_URL = "https://training.galaxyproject.org/training-material/stats/"

FIELDS = [
    "tutorials", "topics", "learning_paths", "faqs", "workflows",
    "videos", "videos_hours", "news_posts", "contributors",
    "events", "supporting_organisations", "years",
]
LABELS = {
    "tutorials": "Tutorials", "topics": "Topics",
    "learning_paths": "Learning Paths", "faqs": "FAQs",
    "workflows": "Workflows", "videos": "Videos",
    "news_posts": "News Posts",
    "contributors": "Contributors", "events": "Events",
    "supporting_organisations": "Supporting Organisations",
    "years": "Years",
}
NUM = r"([0-9]+(?:\.[0-9]+)?)"

PREVSAFE = [k for k in FIELDS if k not in ("videos_hours", "years")]


def fetch(url):
    return urllib.request.urlopen(url, timeout=120).read().decode("utf-8", "replace")


def unnest(text):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text.replace("&nbsp;", " ")))


def parse_stats(text):
    flat = unnest(text)
    stats = {}
    for key, label in LABELS.items():
        m = re.search(NUM + r"\s+" + re.escape(label), flat)
        if m:
            stats[key] = float(m.group(1)) if "." in m.group(1) else int(m.group(1))
    m = re.search(NUM + r"\s+Videos\s+\(([0-9]+(?:\.[0-9]+)?)h\)", flat)
    if m:
        stats["videos_hours"] = float(m.group(2))
    return stats


def cell(stats, key):
    v = stats.get(key)
    if v is None:
        return ""
    return str(int(v)) if v == int(v) else f"{v}"


def main():
    out_dir = Path(__file__).resolve().parent / "data"
    out_dir.mkdir(exist_ok=True)

    cache = {}
    def snapshot(name):
        if name not in cache:
            print(f"fetching archive snapshot {name} ...")
            cache[name] = parse_stats(fetch(
                f"https://training.galaxyproject.org/archive/{name}/stats/"
            ))
        return cache[name]

    print("fetching live stats page ...")
    current = parse_stats(fetch(CURRENT_URL))

    with open(out_dir / "gtn_archive_stats.tsv", "w", encoding="utf-8") as fh:
        fh.write("\t".join(["year"] + FIELDS) + "\n")
        for year, snap in END_SNAPSHOTS.items():
            stats = snapshot(snap)
            fh.write(f"{year}\t" + "\t".join(cell(stats, k) for k in FIELDS) + "\n")
        fh.write("current\t" + "\t".join(cell(current, k) for k in FIELDS) + "\n")

    with open(out_dir / "gtn_archive_new_per_year.tsv", "w", encoding="utf-8") as fh:
        fh.write("\t".join(["year"] + PREVSAFE) + "\n")
        for year in START_SNAPSHOTS:
            start = START_SNAPSHOTS[year]
            if start is None:
                continue
            base, newer = snapshot(start), snapshot(END_SNAPSHOTS[year])
            new = {k: int(newer[k]) - int(base[k])
                   if k in newer and k in base else ""
                   for k in PREVSAFE}
            fh.write(year + "\t" + "\t".join(f"{v}" for v in new.values()) + "\n")

    print("\nwrote: gtn_archive_stats.tsv, gtn_archive_new_per_year.tsv")
    print("\nAbsolute year-end counts:\n" +
          open(out_dir / "gtn_archive_stats.tsv", "r").read())
    print("New per year:\n" +
          open(out_dir / "gtn_archive_new_per_year.tsv", "r").read())


if __name__ == "__main__":
    main()