#!/usr/bin/env python3
"""Collect citations for specific articles (Galaxy NAR papers) via open APIs.

Sources
-------
- Crossref API  : metadata + `is-referenced-by-count` (self-reported count)
- OpenAlex API  : full list of citing works (title, year, venue, DOI, authors)
- Semantic Scholar (optional, --semanticscholar): independent citationCount

No API keys required. Uses the "polite pool" with a mailto contact.

Usage
-----
    python3 citations.py                          # both Galaxy NAR papers
    python3 citations.py -d 10.1093/nar/gkae410   # any DOI
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

MAILTO = "paul.zierep@gmail.com"
PAPERS = [
    {
        "doi": "10.1093/nar/gkag469",
        "label": "Galaxy 2026 update (NAR 54, W105-W116)",
    },
    {
        "doi": "10.1093/nar/gkae410",
        "label": "Galaxy 2024 update (NAR 52, W83-W94)",
    },
]
HEADERS = {"User-Agent": f"galaxy-kpi/1.0 (mailto:{MAILTO})"}


def get_json(url, params=None):
    params = dict(params or {})
    params.setdefault("mailto", MAILTO)
    url = url + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.load(resp)


def crossref(doi):
    data = get_json(f"https://api.crossref.org/works/{urllib.parse.quote(doi)}")
    m = data["message"]
    year = m.get("issued", {}).get("date-parts", [[None]])[0][0]
    return {
        "doi": doi,
        "title": m.get("title", [""])[0],
        "container": m.get("container-title", [""])[0],
        "year": year,
        "is-referenced-by-count": m.get("is-referenced-by-count", 0),
    }


def openalex_work(doi):
    data = get_json(f"https://api.openalex.org/works/https://doi.org/{doi}")
    return data


def openalex_citing(work_id):
    """Page through OpenAlex works citing `work_id`."""
    out = []
    cursor = "*"
    while cursor:
        params = {"filter": f"cites:{work_id}", "per-page": 100, "cursor": cursor}
        data = get_json("https://api.openalex.org/works", params)
        for w in data.get("results", []):
            authors = ", ".join(
                a.get("author", {}).get("display_name", "")
                for a in w.get("authorships", [])
            )[:300]
            loc = w.get("primary_location") or {}
            out.append(
                {
                    "citing_doi": (w.get("doi") or "").replace("https://doi.org/", ""),
                    "year": w.get("publication_year"),
                    "title": w.get("title", ""),
                    "venue": (loc.get("source") or {}).get("display_name", ""),
                    "authors": authors,
                }
            )
        cursor = data.get("meta", {}).get("next_cursor")
        if data.get("meta", {}).get("count") <= 0:
            break
    return out


def semantic_scholar_citations(doi):
    data = get_json(
        f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}",
        {"fields": "citationCount,title"},
    )
    return data.get("citationCount")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "-d", "--doi", action="append", default=[],
        help="additional DOIs to collect (repeatable)",
    )
    ap.add_argument("--semanticscholar", action="store_true",
                    help="also query Semantic Scholar for citation counts")
    args = ap.parse_args()

    papers = list(PAPERS)
    for doi in args.doi:
        papers.append({"doi": doi, "label": ""})

    out_dir = Path(__file__).resolve().parent / "data"
    out_dir.mkdir(exist_ok=True)

    summary = []
    for p in papers:
        doi = p["doi"]
        print(f"\n=== {p['label']}  ({doi}) ===")
        meta = crossref(doi)
        print(f"  {meta['title']}")
        print(f"  {meta['container']} ({meta['year']})")
        print(f"  Crossref is-referenced-by-count: {meta['is-referenced-by-count']}")

        work = openalex_work(doi)
        work_id = work["id"]
        oa_count = work.get("cited_by_count", 0)
        print(f"  OpenAlex cited_by_count: {oa_count}")

        citing = openalex_citing(work_id)
        print(f"  OpenAlex citing works fetched: {len(citing)}")

        ss = None
        if args.semanticscholar:
            for attempt in range(3):
                try:
                    ss = semantic_scholar_citations(doi)
                    print(f"  Semantic Scholar citationCount: {ss}")
                    break
                except urllib.error.HTTPError as exc:
                    if exc.code == 429:
                        time.sleep(5 * (attempt + 1))
                    else:
                        print(f"  Semantic Scholar failed: {exc}")
                        break
                except Exception as exc:  # noqa: BLE001
                    print(f"  Semantic Scholar failed: {exc}")
                    break

        by_year = {}
        for c in citing:
            by_year[c["year"]] = by_year.get(c["year"], 0) + 1

        slug = doi.replace("/", "_")
        citing_path = out_dir / f"citations_{slug}.tsv"
        with open(citing_path, "w", encoding="utf-8") as fh:
            fh.write("citing_doi\tyear\ttitle\tvenue\tauthors\n")
            for c in sorted(citing, key=lambda c: (c["year"] or 0, c["title"])):
                fh.write(
                    f"{c['citing_doi']}\t{c['year']}\t"
                    f"{c['title']}\t{c['venue']}\t{c['authors']}\n"
                )
        print(f"  wrote {citing_path}")

        bc = f"{citing_path.name}::count"
        summary.append(
            {
                "doi": doi,
                "title": meta["title"],
                "cited_by_crossref": meta["is-referenced-by-count"],
                "cited_by_openalex": oa_count,
                "cited_by_semanticscholar": ss if ss is not None else "",
                "openalex_listed": len(citing),
                "by_year": by_year,
            }
        )

    with open(out_dir / "citations_summary.tsv", "w", encoding="utf-8") as fh:
        fh.write("doi\ttitle\tcrossref_count\topenalex_count\tsemanticscholar_count\topenalex_listed\n")
        for s in summary:
            fh.write(
                f"{s['doi']}\t{s['title']}\t{s['cited_by_crossref']}\t"
                f"{s['cited_by_openalex']}\t{s['cited_by_semanticscholar']}\t"
                f"{s['openalex_listed']}\n"
            )
    print(f"\nwrote {out_dir / 'citations_summary.tsv'}")

    # yearly distribution table per paper
    years = sorted({y for s in summary for y in s["by_year"]})
    ypath = out_dir / "citations_by_year.tsv"
    with open(ypath, "w", encoding="utf-8") as fh:
        fh.write("year\t" + "\t".join(s["doi"] for s in summary) + "\n")
        for y in years:
            fh.write(str(y) + "\t" + "\t".join(str(s["by_year"].get(y, 0)) for s in summary) + "\n")
    print(f"wrote {ypath}")


if __name__ == "__main__":
    main()