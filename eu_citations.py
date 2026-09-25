#!/usr/bin/env python3
"""Publications citing the European Galaxy server (UseGalaxy.eu).

The Galaxy Hub maintains the bibliography of publications citing Galaxy Europe
in `citations-eu.bib`, exported from the Galaxy Publications Zotero group
(https://www.zotero.org/groups/1732893/items, tag `>UseGalaxy.eu`; both sources
contain the same 1,731 entries).

Usage
-----
    python3 eu_citations.py     # -> data/eu_citations_by_year.tsv
"""

import re
import urllib.request
from pathlib import Path

BIB_URL = ("https://raw.githubusercontent.com/galaxyproject/galaxy-hub/main/"
           "content/eu/citations/citations-eu.bib")


def fetch(url):
    return urllib.request.urlopen(url, timeout=120).read().decode("utf-8")


def main():
    out_dir = Path(__file__).resolve().parent / "data"
    out_dir.mkdir(exist_ok=True)

    txt = fetch(BIB_URL)
    entries = [e for e in re.split(r"\n(?=@\w+\{)", txt) if e.startswith("@")]

    years = {}
    no_year = 0
    for e in entries:
        m = re.search(r"\n\s*year\s*=\s*\{(.+?)\},?\n", e, re.S)
        y = m.group(1).strip() if m else ""
        if y.isdigit():
            years.setdefault(int(y), 0)
            years[int(y)] += 1
        else:
            no_year += 1

    out = out_dir / "eu_citations_by_year.tsv"
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("year\tcitations\n")
        for y in sorted(years):
            fh.write(f"{y}\t{years[y]}\n")

    print(f"Publications citing UseGalaxy.eu: {len(entries)} total "
          f"({no_year} without year field)")
    for y in sorted(years):
        if y >= 2018:
            print(f"  {y}: {years[y]}")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()