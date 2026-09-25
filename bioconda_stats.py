#!/usr/bin/env python3
"""Easy bioconda KPIs from the bioconda-stats repo (branch `data`).

Beyond the yearly channel total (see bioconda_downloads.py) this computes:
  - downloads per year split by platform/subdir
  - per-package downloads per year (top packages, watchlist)
  - number of distinct packages downloaded per year, and new packages per year

Data:
  channel.tsv (branch head, one row per day):
      package-downloads/anaconda.org/bioconda/channel.tsv
  packages.tsv (snapshots tagged by date, one cumulative total per package):
      package-downloads/anaconda.org/bioconda/packages.tsv  @ <YYYY-MM-DD>

Because every snapshot is cumulative, a year's downloads telescope to:

  downloads(Y) = total(Dec 31, Y) - total(Dec 31, Y-1)

Usage
-----
    python3 bioconda_stats.py

Needs network access to raw.githubusercontent.com. Writes several TSVs to
`data/`.
"""

import sys
import urllib.request
from collections import Counter
from pathlib import Path

YEARS = (2023, 2024, 2025)
BOUNDARIES = (2022, 2023, 2024, 2025)  # cum boundary years for Y = B..B+1

CHANNEL_URL = (
    "https://raw.githubusercontent.com/bioconda/bioconda-stats/data/"
    "package-downloads/anaconda.org/bioconda/channel.tsv"
)
PACKAGES_URL = (
    "https://raw.githubusercontent.com/bioconda/bioconda-stats/{tag}/"
    "package-downloads/anaconda.org/bioconda/packages.tsv"
)

TOP_N = 20
WATCHLIST = [
    "samtools", "bcftools", "bedtools", "fastp", "fastqc", "multiqc",
    "trim-galore", "cutadapt", "bwa", "star", "bowtie2", "kallisto",
    "salmon", "sra-tools", "snakemake", "picard",
]


def fetch(url):
    return urllib.request.urlopen(url, timeout=180).read().decode("utf-8")


def fetch_channel():
    """Return {date: {subdir: total}} using channel.tsv columns."""
    platforms = {}
    text = fetch(CHANNEL_URL)
    lines = text.splitlines()
    header = lines[0].split("\t")
    subdirs = header[1:]
    for line in lines[1:]:
        parts = line.split("\t")
        date = parts[0]
        if not date.startswith("20"):
            continue
        platforms[date] = {
            subdirs[i]: int(parts[1 + i])
            for i in range(len(subdirs))
            if (1 + i < len(parts)) and parts[1 + i].strip().isdigit()
        }
    return platforms


def fetch_package_snapshot(tag):
    """Return {package: cumulative total} for the given date tag."""
    totals = {}
    text = fetch(PACKAGES_URL.format(tag=tag))
    for line in text.splitlines()[1:]:
        parts = line.split("\t")
        if len(parts) >= 2 and parts[1].isdigit():
            totals[parts[0]] = int(parts[1])
    return totals


def main():
    out_dir = Path(__file__).resolve().parent / "data"
    out_dir.mkdir(exist_ok=True)

    channel = fetch_channel()
    snapshots = {b: fetch_package_snapshot(f"{b}-12-31") for b in BOUNDARIES}

    rows = []
    top_rows = []
    counts_rows = []
    watch_rows = []
    for year in YEARS:
        lo, hi = f"{year - 1}-12-31", f"{year}-12-31"
        if lo not in channel or hi not in channel:
            sys.exit(f"missing channel boundary rows for {year}")

        total = channel[hi]["total"] - channel[lo]["total"]
        print(f"\nbioconda downloads {year}: {total:,}")

        platform_rows = []
        for sub in channel[hi]:
            if sub == "total":
                continue
            prev = channel[lo].get(sub)
            cur = channel[hi][sub]
            if prev is None or cur is None:
                continue
            d = cur - prev
            if d > 0:
                platform_rows.append((sub, d))
        platform_rows.sort(key=lambda x: -x[1])
        for sub, d in platform_rows:
            print(f"  {sub:>14}: {d:>12,}  ({100 * d / total:.1f}%)")
        rows.append({"year": year, "platforms": platform_rows})

        prev_pkg = snapshots[year - 1]
        cur_pkg = snapshots[year]
        per_pkg = {p: cur_pkg[p] - prev_pkg.get(p, 0)
                   for p in cur_pkg if cur_pkg[p] > prev_pkg.get(p, 0)}
        active = sum(1 for v in per_pkg.values() if v > 0)
        new_pkgs = sorted(p for p in per_pkg if p not in prev_pkg and per_pkg[p] > 0)
        print(f"  distinct packages downloaded: {active:,}; new this year: {len(new_pkgs):,}")

        top = sorted(per_pkg.items(), key=lambda x: -x[1])[:TOP_N]
        for rank, (pkg, d) in enumerate(top, 1):
            top_rows.append((year, rank, pkg, d))
            print(f"    #{rank:<3}{pkg:<32}{d:>12,}")

        counts_rows.append((year, total, active, len(new_pkgs)))

        for pkg in WATCHLIST:
            d = per_pkg.get(pkg, 0)
            watch_rows.append((year, pkg, d))

    # ---- write files ----
    with open(out_dir / "bioconda_platforms.tsv", "w", encoding="utf-8") as fh:
        fh.write("year\tsubdir\tdownloads\n")
        for r in rows:
            for sub, d in r["platforms"]:
                fh.write(f"{r['year']}\t{sub}\t{d}\n")

    with open(out_dir / "bioconda_top_packages.tsv", "w", encoding="utf-8") as fh:
        fh.write("year\trank\tpackage\tdownloads\n")
        for year, rank, pkg, d in top_rows:
            fh.write(f"{year}\t{rank}\t{pkg}\t{d}\n")

    with open(out_dir / "bioconda_package_counts.tsv", "w", encoding="utf-8") as fh:
        fh.write("year\ttotal_downloads\tactive_packages\tnew_packages\n")
        for year, total, active, new_pk in counts_rows:
            fh.write(f"{year}\t{total}\t{active}\t{new_pk}\n")

    with open(out_dir / "bioconda_watchlist.tsv", "w", encoding="utf-8") as fh:
        fh.write("year\tpackage\tdownloads\n")
        for year, pkg, d in watch_rows:
            fh.write(f"{year}\t{pkg}\t{d}\n")

    print("\nwrote: bioconda_platforms.tsv, bioconda_top_packages.tsv, "
          "bioconda_package_counts.tsv, bioconda_watchlist.tsv")


if __name__ == "__main__":
    main()