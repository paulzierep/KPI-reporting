#!/usr/bin/env python3
"""Combine Galaxy error-report mails, TIaaS mails, and forum support topics by year.

Reads the already-collected data:
- data/galaxy_no_reply_kinds.tsv   (error_report / TIaaS mail counts)
- data/galaxy_help_usegalaxy_eu_topics_by_year.tsv  (new help topic counts)

and writes a single combined table per calendar year.

Usage
-----
    python3 combine_support_kpis.py
"""

from pathlib import Path

YEARS = (2023, 2024, 2025)


def read_kinds(path):
    rows = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines()[1:]:
        parts = line.split("\t")
        if len(parts) >= 3:
            rows[(parts[0], parts[1])] = parts[2]
    return rows


def read_year_counts(path):
    rows = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines()[1:]:
        parts = line.split("\t")
        if len(parts) >= 2:
            rows[parts[0]] = parts[1]
    return rows


def main():
    data = Path(__file__).resolve().parent / "data"

    kinds = read_kinds(data / "galaxy_no_reply_kinds.tsv")
    help_topics = read_year_counts(
        data / "galaxy_help_usegalaxy_eu_topics_by_year.tsv"
    )

    out = data / "combined_support_kpis.tsv"
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(
            "year\terror_report_mails\ttiaas_mails\thelp_topics\t"
            "mails_plus_topics\n"
        )
        print(f"{'year':<6}{'error mails':>12}{'tiaas':>8}{'help topics':>13}{'sum':>10}")
        for year in YEARS:
            err = int(kinds.get((str(year), "error_report"), 0))
            tiaas = int(kinds.get((str(year), "tiaas_request"), 0))
            topics = int(help_topics.get(str(year), 0))
            total = err + tiaas + topics
            fh.write(f"{year}\t{err}\t{tiaas}\t{topics}\t{total}\n")
            print(f"{year:<6}{err:>12,}{tiaas:>8,}{topics:>13,}{total:>10,}")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()