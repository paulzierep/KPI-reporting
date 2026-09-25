#!/usr/bin/env python3
"""Collect citation counts (and optionally citing lists) from Google Scholar.

Google Scholar has no public API, so this scrapes the HTML search results
(title query -> "Cited by N") with a browser User-Agent. Respectful of rate
limits: 2 s between requests. Google may throttle or CAPTCHA; re-run later then.

By default only the per-paper "Cited by" counts are fetched (one request per
paper). With --citing-list it also harvests the complete citing work list per
paper from the `cites=` cluster (10 results per page), which is many requests
(858 citations of the 2024 paper = 86 pages) and far more likely to trigger a
CAPTCHA -- use sparingly.

Usage
-----
    python3 google_scholar_citations.py                  # counts only
    python3 google_scholar_citations.py --citing-list    # counts + full lists
"""

import argparse
import html
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

MAILTO = "paul.zierep@gmail.com"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}
SCHOLAR = "https://scholar.google.com/scholar?hl=en"

PAPERS = [
    ("10.1101/gr.4086505", "Galaxy: A platform for interactive large-scale genome analysis"),
    ("10.1002/0471250953.bi1005s19", "Using Galaxy to Perform Large-Scale Interactive Data Analyses"),
    ("10.1186/gb-2010-11-8-r86", "Galaxy: a comprehensive approach for supporting accessible, reproducible, and transparent computational research in the life sciences"),
    ("10.1002/0471142727.mb1910s89", "Galaxy: A Web-Based Genome Analysis Tool for Experimentalists"),
    ("10.1093/nar/gkw343", "The Galaxy platform for accessible, reproducible and collaborative biomedical analyses: 2016 update"),
    ("10.1093/nar/gky379", "The Galaxy platform for accessible, reproducible and collaborative biomedical analyses: 2018 update"),
    ("10.1093/nar/gkac247", "The Galaxy platform for accessible, reproducible and collaborative biomedical analyses: 2022 update"),
    ("10.1093/nar/gkae410", "The Galaxy platform for accessible, reproducible, and collaborative data analyses: 2024 update"),
    ("10.1093/nar/gkag469", "Galaxy for accessible, reproducible, and collaborative data analyses: 2026 update"),
]

CITED_RE = re.compile(r"Cited by (\d+)")
CITES_RE = re.compile(r"cites=(\d+)")


def get(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8", "replace")


def find_cluster(text):
    m = CITES_RE.search(text)
    return m.group(1) if m else None


def fetch_count(title, retries=3):
    q = urllib.parse.quote('"' + title + '"')
    for attempt in range(retries):
        try:
            page = get(f"{SCHOLAR}&q={q}")
            cited = CITED_RE.findall(page)
            cluster = find_cluster(page)
            if cited and cluster:
                return int(cited[0]), cluster
            print(f"    (empty answer, attempt {attempt + 1}/{retries})")
        except Exception as exc:
            print(f"    (request error: {exc}, attempt {attempt + 1}/{retries})")
        time.sleep(15 * (attempt + 1))
    return None, None


def harvest_citing_list(cluster_id):
    """Parse citing works (title + year) from the cites= cluster, all pages."""
    out = []
    start = 0
    while True:
        page = get(f"{SCHOLAR}&cites={cluster_id}&start={start}")
        blocks = re.split(r'class="gs_r', page)[1:]
        if not blocks:
            break
        parsed = 0
        year_re = re.compile(r"<span class=\"gs_a\">[^<]*")
        for block in blocks:
            title_m = re.search(r'<h3 class="gs_rt"[^>]*>(?:<span class="gs_ctu">)?(?:<a [^>]*>)?(.*?)</a>', block, re.S)
            if not title_m:
                continue
            title = re.sub(r"<[^>]+>", "", title_m.group(1))
            title = html.unescape(title).strip()
            year = None
            a = year_re.search(block)
            if a:
                m = re.search(r"(\d{4})", a.group(0))
                if m:
                    year = int(m.group(1))
            out.append((title, year))
            parsed += 1
        print(f"    cites page {start // 10}: {parsed} works (total {len(out)})")
        if parsed < 10:
            break
        start += 10
        time.sleep(2)
    return out


def load_existing(path):
    done = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines()[1:]:
            parts = line.split("\t")
            if len(parts) >= 3:
                try:
                    done[parts[0]] = (int(parts[1]), parts[2])
                except ValueError:
                    done[parts[0]] = (None, parts[2])
    return done


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--citing-list", action="store_true",
                    help="also harvest full citing work lists from Scholar"
                         " (slow, higher risk of CAPTCHA)")
    args = ap.parse_args()

    out_dir = Path(__file__).resolve().parent / "data"
    out_dir.mkdir(exist_ok=True)
    summary = out_dir / "google_scholar_citations.tsv"
    existing = load_existing(summary)

    rows = []
    for doi, title in PAPERS:
        if doi in existing:
            count, cluster = existing[doi]
            print(f"\n=== {title[:60]}... ({doi}) === (cached: {count})")
        else:
            print(f"\n=== {title[:60]}... ({doi}) ===")
            count, cluster = fetch_count(title)
            if count is None:
                print(f"  Google Scholar cited by: n/a (blocked/empty)  cluster: {cluster}")
            else:
                print(f"  Google Scholar cited by: {count:,}   cluster: {cluster}")
        if count is not None and cluster is not None and args.citing_list:
            citing = harvest_citing_list(cluster)
            path = out_dir / f"google_scholar_citing_{doi.replace('/', '_')}.tsv"
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("year\ttitle\n")
                for t, y in sorted(citing, key=lambda c: (c[1] or 0)):
                    fh.write(f"{y}\t{t}\n")
            print(f"  wrote {path} ({len(citing)} works)")
        rows.append((doi, count, cluster))
        time.sleep(8)

    summary = out_dir / "google_scholar_citations.tsv"
    with open(summary, "w", encoding="utf-8") as fh:
        fh.write("doi\tgoogle_scholar_cited_by\tcluster_id\n")
        for doi, count, cluster in rows:
            fh.write(f"{doi}\t{count}\t{cluster}\n")
    print(f"\nwrote {summary}")


if __name__ == "__main__":
    main()