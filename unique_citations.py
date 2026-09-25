#!/usr/bin/env python3
"""Count unique citing works across all tracked Galaxy NAR papers, per year.

Reads the per-paper citing-work lists produced by `citations.py` from
data/citations_<doi>.tsv, deduplicates citing works by DOI across papers, and
counts unique citations for a given year range (default 2023-2025).

Usage
-----
    python3 unique_citations.py            # unique citations 2023-2025
    python3 unique_citations.py 2024       # single year
    python3 unique_citations.py 2021 2025  # year range
"""

import sys
from collections import Counter
from pathlib import Path

DEFAULT_RANGE = (2023, 2025)


def load_citing_works(data_dir):
    """Return {citing_doi: year} merged across all paper citation lists."""
    works = {}
    for path in sorted(data_dir.glob("citations_*.tsv")):
        if path.name.startswith("citations_summary") or path.name.startswith("citations_by_year"):
            continue
        for line in path.read_text(encoding="utf-8").splitlines()[1:]:
            parts = line.split("\t")
            if len(parts) < 2:
                continue
            doi = parts[0]
            if not doi:
                continue
            year = parts[1]
            try:
                year = int(year) if year else None
            except ValueError:
                year = None
            if doi not in works:  # first paper wins; keep earliest record
                works[doi] = year
    return works


def main():
    args = [int(a) for a in sys.argv[1:] if a.isdigit()]
    lo, hi = (args[0], args[-1]) if args else DEFAULT_RANGE

    data_dir = Path(__file__).resolve().parent / "data"
    works = load_citing_works(data_dir)

    selected = {doi: y for doi, y in works.items() if y is not None and lo <= y <= hi}

    per_year = Counter(y for y in selected.values())
    out = data_dir / f"unique_citations_{lo}-{hi}.tsv"
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("year\tunique_citing_works\n")
        for y in range(lo, hi + 1):
            fh.write(f"{y}\t{per_year.get(y, 0)}\n")
        fh.write(f"total\t{len(selected)}\n")
    print(f"unique citing works {lo}-{hi} across all tracked Galaxy papers: {len(selected):,}")
    for y in range(lo, hi + 1):
        print(f"  {y}: {per_year.get(y, 0):,}")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()