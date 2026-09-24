#!/usr/bin/env python3
"""Print the total number of bioconda package downloads per calendar year.

Data source: https://github.com/bioconda/bioconda-stats (branch `data`)

That repository commits a daily, cumulative (all-time) download total for the
whole bioconda channel to

    package-downloads/anaconda.org/bioconda/channel.tsv

with one row per day and each snapshot tagged by its date. Because the numbers
are cumulative, downloads in a calendar year telescope to:

    downloads(Y) = channel_total(Dec 31, Y) - channel_total(Dec 31, Y-1)

Usage
-----
    python3 bioconda_downloads.py          # prints 2023, 2024, 2025
    python3 bioconda_downloads.py 2024     # prints a single year

Needs network access to raw.githubusercontent.com.
"""

import sys
import urllib.request

YEARS = (2023, 2024, 2025)
CHANNEL_URL = (
    "https://raw.githubusercontent.com/bioconda/bioconda-stats/data/"
    "package-downloads/anaconda.org/bioconda/channel.tsv"
)


def fetch_channel_totals():
    """Return {YYYY-MM-DD: cumulative channel total} from channel.tsv."""
    totals = {}
    text = urllib.request.urlopen(CHANNEL_URL, timeout=120).read().decode("utf-8")
    for line in text.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2 and parts[0].startswith("20") and parts[1].isdigit():
            totals[parts[0]] = int(parts[1])
    return totals


def yearly_downloads(totals, year):
    return totals[f"{year}-12-31"] - totals[f"{year - 1}-12-31"]


def main():
    totals = fetch_channel_totals()
    args = [int(a) for a in sys.argv[1:] if a.isdigit()] or list(YEARS)
    for year in args:
        if f"{year}-12-31" not in totals or f"{year - 1}-12-31" not in totals:
            sys.exit(f"no boundary snapshots available for {year}")
        print(f"bioconda downloads {year}: {yearly_downloads(totals, year):,}")


if __name__ == "__main__":
    main()