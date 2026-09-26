#!/usr/bin/env python3
"""Find FREIBURG_GALAXY_TEAM publications for the Galaxy Hub freiburg.bib.

Scans the ORCID records of everyone listed under ``freiburg`` in the Galaxy Hub
``content/people/people.yaml`` and collects publications relevant to the Freiburg
Galaxy team:

1. fetch each person's works from the ORCID public API
2. estimate the person's "join year" as the earliest year of any Galaxy-related
   work — only a STRICT Galaxy match (title/journal mentions galaxy/usegalaxy/
   toolshed/bioconda/biocontainer/planemo/orione) counts; people with no Galaxy
   work at all are skipped. Publications before that are dropped.
3. drop works already present in freiburg.bib (DOI match, then normalized title)
4. prefer the journal version over a preprint when the same title appears twice
5. drop preprint versions (bioRxiv/medRxiv/Research Square, …) whose journal
   version is already in freiburg.bib or among the new candidates

The remaining works are written as clean BibTeX (via DOI content negotiation) to
``data/candidates.bib`` and summarized in ``data/freiburg-candidates.md``.

Sources
-------
* people/ORCIDs: https://raw.githubusercontent.com/galaxyproject/galaxy-hub/main/content/people/people.yaml
* existing bibliography: https://raw.githubusercontent.com/galaxyproject/galaxy-hub/main/content/freiburg/citations/freiburg.bib

Usage
-----
    python3 freiburg_publications.py              # fetch from galaxy-hub main
    python3 freiburg_publications.py --out .      # write report+bib to cwd
    python3 freiburg_publications.py --only paulzierep
    python3 freiburg_publications.py --yaml content/people/people.yaml \
        --bib content/freiburg/citations/freiburg.bib   # local files

Output
------
* data/candidates.bib          — BibTeX entries ready to merge into freiburg.bib
* data/freiburg-candidates.md  — human-readable report
"""

import argparse
import difflib
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

GALAXY_HUB = "https://raw.githubusercontent.com/galaxyproject/galaxy-hub/main"
ORCID_API = "https://pub.orcid.org/v3.0/{orcid}/works"
USER_AGENT = "galaxy-hub-freiburg-citations/1.0"
TIMEOUT = 60
SLEEP = 1.0  # ORCID public API rate limit

# Broad terms hinting at Galaxy involvement (informational flag only)
GALAXY_KEYWORDS = [
    "galaxy",
    "workflow",
    "bioconda",
    "biocontainer",
    "toolshed",
    "metagenom",
    "amplicon",
    "sequencing",
    "ngs",
    "rna-seq",
    "rnaseq",
    "single-cell",
    "training material",
    "planemo",
    "orione",
]

# STRICT terms that unambiguously identify Galaxy work. Used only for the
# join-year estimate ("earliest Galaxy publication"). ``galaxy`` also covers
# usegalaxy / microgalaxy / galaxy-tools / galaxy-api etc.
GALAXY_JOIN_KEYWORDS = [
    "galaxy",
    "usegalaxy",
    "toolshed",
    "bioconda",
    "biocontainer",
    "planemo",
    "orione",
]

BIB_DOI = re.compile(r"DOI\s*=\s*\{([^}]+)\}", re.IGNORECASE)
BIB_TITLE = re.compile(r"title\s*=\s*\{([^}]+)\}", re.IGNORECASE)
BIB_KEY = re.compile(r"@[A-Za-z]+\{([^,\n]+),")

# DOI patterns of preprint servers / non-journal venues
PREPRINT_DOI = re.compile(
    r"10\.1101/|10\.21203/|10\.20944/|10\.37044/|10\.52825/|10\.17504/"
    r"|medrxiv|biorxiv|preprint",
    re.IGNORECASE,
)


def fetch(url: str, headers: dict | None = None) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return response.read()


def parse_people_yaml(yaml_text: str) -> dict[str, dict]:
    """Minimal YAML reader for the freiburg block of people.yaml (no PyYAML).

    Supports the subset used there: nested ``freiburg:`` mapping, 2-level entries
    with ``key: value`` scalar fields, quirk: ``bio: |`` heredocs are ignored.
    Returns {person_key: {field: value}}.
    """
    people: dict[str, dict] = {}
    current: dict | None = None
    in_freiburg = False
    for line in yaml_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#") or not stripped:
            continue
        indent = len(line) - len(line.lstrip())
        if indent == 0:
            in_freiburg = stripped.rstrip(":") == "freiburg"
            current = None
            continue
        if not in_freiburg:
            continue
        if indent == 4 and ":" in stripped and not stripped.startswith("-"):
            key = stripped.rstrip(":").strip()
            current = people.setdefault(key, {})
            continue
        if indent == 8 and current is not None and ":" in stripped:
            field, _, value = stripped.partition(":")
            field = field.strip()
            value = value.strip().strip('"').strip("'").strip()
            if value in ("|", ">") or field in ("bio",):
                continue
            current[field] = value
    return people


def extract_work(w: dict) -> tuple[str, str | None]:
    title = w.get("title")
    if isinstance(title, dict):
        inner = title.get("title")
        if isinstance(inner, dict):
            title = inner.get("value")
        else:
            title = title.get("value")
    title = title or ""
    journal = w.get("journal-title")
    if isinstance(journal, dict):
        journal = journal.get("value")
    return title, journal


def fetch_orcid_works(orcid: str) -> list[dict]:
    data = json.loads(fetch(ORCID_API.format(orcid=orcid), {"Accept": "application/json"}))
    groups: dict[str, dict] = {}
    for group in data.get("group", []):
        for summary in group.get("work-summary", []):
            title, journal = extract_work(summary)
            if not title:
                continue
            doi = next(
                (
                    i.get("external-id-value")
                    for i in ((summary.get("external-ids") or {}).get("external-id") or [])
                    if i.get("external-id-type") == "doi"
                ),
                None,
            )
            year = (summary.get("publication-date") or {}).get("year") or {}
            year = year.get("value")
            if s := groups.setdefault(title, {"title": title, "journal": journal, "doi": doi, "year": year}):
                if doi and not s.get("doi"):
                    s["doi"] = doi
                if year and not s.get("year"):
                    s["year"] = year
                if not s.get("journal") and journal:
                    s["journal"] = journal
    return list(groups.values())


def is_galaxy_related(title: str, journal: str | None) -> bool:
    haystack = " ".join(filter(None, [title, journal or ""])).lower()
    return any(kw.lower() in haystack for kw in GALAXY_KEYWORDS)


def is_galaxy_join(title: str, journal: str | None) -> bool:
    """STRICT Galaxy match used for the join-year proxy.

    ``galaxy`` alone catches usegalaxy/microgalaxy/galaxy-* tool names, so only
    titles/journals that are unambiguously about Galaxy qualify.
    """
    haystack = " ".join(filter(None, [title, journal or ""])).lower()
    return any(kw.lower() in haystack for kw in GALAXY_JOIN_KEYWORDS)


def norm_title(title: str) -> str:
    """Normalize a title for matching, ignoring preprint/version markers."""
    title = title or ""
    title = re.sub(r"\[version[^\]]*\]", "", title, flags=re.IGNORECASE)
    title = re.sub(r"\((preprint|protocol)[^)]*\)", "", title, flags=re.IGNORECASE)
    return re.sub(r"[^a-z0-9]+", "", title.lower())


def load_bib_text(text: str) -> tuple[set[str], set[str], set[str], set[str]]:
    dofs, titles, titles_raw, keys = set(), set(), set(), set()
    for m in BIB_DOI.finditer(text):
        dofs.add(m.group(1).strip().lower())
    for m in BIB_TITLE.finditer(text):
        titles.add(norm_title(m.group(1)))
        titles_raw.add(m.group(1).strip())
    for m in BIB_KEY.finditer(text):
        keys.add(m.group(1).strip())
    return dofs, titles, titles_raw, keys


def bibtex_from_doi(doi: str) -> str | None:
    """Canonical BibTeX entry from the CrossRef API.

    CrossRef has proper ``author = {Family, Given and …}`` records (and, for
    journal articles, volume/number/pages), unlike DOI content negotiation,
    which sometimes returns garbage names (e.g. ``not provided, anna.henger``
    from protocols.io) or HTML-tagged titles.
    """
    try:
        data = json.loads(
            fetch(f"https://api.crossref.org/works/{doi}").decode("utf-8", errors="replace")
        )["message"]
    except Exception:  # noqa: BLE001
        return None

    title = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", " ".join(data.get("title") or []))).strip()
    if not title:
        title = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", " ".join(data.get("subtitle") or []))).strip()
    if not title:
        return None

    authors = data.get("author") or []
    auth_str = " and ".join(
        f"{a.get('family', '')}, {a.get('given', '')}".strip(" ,") for a in authors
    )
    year = ((data.get("published-print") or data.get("published-online")
             or data.get("issued") or {}).get("date-parts", [[None]])[0][0])
    kind = "article" if data.get("type") in ("journal-article", "proceedings-article") else "misc"
    fields = [("title", title)]
    for fld, getter in (("volume", lambda: data.get("volume")), ("number", lambda: data.get("issue")),
                        ("pages", lambda: data.get("page"))):
        v = getter()
        if v:
            fields.append((fld, str(v)))
    if journal := (data.get("container-title") or [""])[0]:
        fields.append(("journal", journal))
    if auth_str:
        fields.append(("author", auth_str))
    if year:
        fields.append(("year", str(year)))
    fields.append(("DOI", doi))

    key = (re.sub(r"[^A-Za-z]+", "", authors[0].get("family", "Untitled")) or "Untitled").capitalize()
    key = f"{key}_{year}" if year else key
    lines = [f"@{kind}{{{key},"]
    for i, (f, v) in enumerate(fields):
        lines.append(f"  {f} = {{{v}}}{',' if i < len(fields) - 1 else ''}")
    lines.append("}")
    return "\n".join(lines)


USERNAME_AUTHOR_FIX = {"anna.henger": "Henger, Anna"}


def clean_bibtex_entry(entry: str) -> str:
    """Fix CrossRef author quirks, e.g. protocols.io "not provided, anna.henger".

    The trailing username is an ORCID-linked display handle; fix the names we
    recognise. Any remaining "not provided" author is dropped from the list.
    """
    for username, real in USERNAME_AUTHOR_FIX.items():
        entry = entry.replace(f"not provided, {username}", real)
    pattern = r"\s+and\s+not provided[^,]*?, [^}]*?(?=\s+and\s+|\s*\})"
    return re.sub(pattern, "", entry, flags=re.IGNORECASE)


def entry_key(entry: str) -> str:
    return BIB_KEY.search(entry).group(1).strip()


def dedupe_keys(existing: set[str], entries: list[str]) -> list[str]:
    """Rename candidate keys that collide with the existing bib or each other."""
    taken = set(existing)
    out = []
    for e in entries:
        key = entry_key(e)
        if key not in taken:
            taken.add(key)
            out.append(e)
            continue
        stem = re.sub(r"\d+$", "", key)
        suffix, n = 1, 1
        while True:
            new_key = f"{stem}{n}"
            n += 1
            if new_key not in taken:
                break
        taken.add(new_key)
        out.append(e.replace(f"{{{key},", f"{{{new_key},", 1))
    return out





def dedupe_candidates(candidates: list[dict]) -> list[dict]:
    """Drop duplicate titles, preferring the version with a journal (published).

    Also collapses works that share a DOI but were entered on ORCID under
    slightly different titles (e.g. preprint vs journal wording), and drops
    same-title duplicates with different DOIs (e.g. an ORCID re-entry) keeping
    the earliest year.
    """
    best: dict[str, dict] = {}
    order: list[str] = []
    for c in candidates:
        key = c.get("doi") and f"doi:{c['doi'].lower()}" or f"title:{norm_title(c['title'])}"
        cur = best.get(key)
        journal = bool(c.get("journal"))
        cur_journal = bool(cur and cur.get("journal"))
        if cur is None or (journal and not cur_journal):
            if cur is None:
                order.append(key)
            best[key] = c

    distinct = [best[k] for k in order]

    # title-level collapse: same title under two different DOIs keeps earliest
    by_title: dict[str, dict] = {}
    t_order: list[str] = []
    for c in distinct:
        tk = f"title:{norm_title(c['title'])}"
        cur = by_title.get(tk)
        if cur is None or (c.get("year") or 9999) < (cur.get("year") or 9999):
            if cur is None:
                t_order.append(tk)
            by_title[tk] = c
    return [by_title[k] for k in t_order]


def drop_preprint_twins(candidates: list[dict], existing_titles: set[str]) -> list[dict]:
    """Drop preprint versions (bioRxiv/medRxiv/Research Square/…) when an
    equivalent *journal* version exists.

    A journal twin is looked up first in the already published bibliography
    (``existing_titles``) and then among the other candidates.  Titles rarely
    match verbatim (e.g. "Planemo: a command-line toolkit…" vs "The Planemo
    toolkit…"), so a fuzzy similarity threshold is used.
    """
    def stripped(title: str) -> str:
        return re.sub(r"<[^>]+>", "", title or "").lower()

    def fuzzy(t1: str, t2: str) -> float:
        return difflib.SequenceMatcher(None, stripped(t1), stripped(t2)).ratio()

    def journal_twin(c: dict) -> bool:
        for t in existing_titles:
            if c["title"] and t and fuzzy(c["title"], t) >= 0.72:
                return True
        for other in candidates:
            if other is c:
                continue
            if not bool(other.get("journal")):
                continue
            if c["title"] and other["title"] and fuzzy(c["title"], other["title"]) >= 0.72:
                return True
        return False

    keep = []
    for c in candidates:
        if c.get("doi") and PREPRINT_DOI.search(c["doi"]) and journal_twin(c):
            continue
        keep.append(c)
    return keep


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--yaml", default=f"{GALAXY_HUB}/content/people/people.yaml", help="people.yaml (URL or path)")
    parser.add_argument("--bib", default=f"{GALAXY_HUB}/content/freiburg/citations/freiburg.bib",
                        help="freiburg.bib (URL or path)")
    parser.add_argument("--out-dir", default=None, help="output dir (default: ./data)")
    parser.add_argument("--only", default=None, help="only process this people.yaml key (e.g. paulzierep)")
    args = parser.parse_args()

    def read_source(src: str) -> str:
        if src.startswith(("http://", "https://")):
            return fetch(src).decode("utf-8", errors="replace")
        return Path(src).read_text(encoding="utf-8")

    people = parse_people_yaml(read_source(args.yaml))
    existing_dois, existing_titles, existing_titles_raw, existing_keys = load_bib_text(read_source(args.bib))

    candidates: list[dict] = []
    report_lines: list[str] = []
    for key, info in people.items():
        if args.only and key != args.only:
            continue
        orcid = info.get("orcid")
        name = info.get("name", key)
        alumni = bool(info.get("alumni"))
        if not orcid:
            report_lines.append(f"## {name} (`{key}`) — skipped: no ORCID")
            continue

        try:
            works = fetch_orcid_works(orcid)
        except Exception as err:  # noqa: BLE001
            report_lines.append(f"## {name} (`{key}`) — ERROR fetching ORCID {orcid}: {err}")
            continue
        time.sleep(SLEEP)

        galaxy_years = [
            int(w["year"]) for w in works
            if w.get("year") and is_galaxy_join(w["title"], w.get("journal"))
        ]
        join_year = min(galaxy_years) if galaxy_years else None
        if join_year is None:
            report_lines.append(
                f"## {name} (`{key}`) — skipped: no STRICT Galaxy-related work on ORCID, "
                f"cannot estimate join year"
            )
            continue

        ok, skipped = [], []
        for w in works:
            title = w["title"]
            year = w.get("year")
            doi = w.get("doi")
            journal = w.get("journal")
            try:
                y = int(year)
            except (TypeError, ValueError):
                continue
            if join_year is not None and y < join_year:
                continue  # before the person likely joined the team
            if doi and doi.lower() in existing_dois:
                skipped.append((w, "already in bib (DOI)"))
                continue
            if norm_title(title) in existing_titles:
                skipped.append((w, "already in bib (title)"))
                continue
            ok.append({"person": key, "name": name, "alumni": alumni, "title": title,
                       "year": y, "doi": doi, "journal": journal,
                       "galaxy_related": is_galaxy_related(title, journal)})

        report_lines.append(f"## {name} (`{key}`){' [alumni]' if alumni else ''} — join≈{join_year}")
        report_lines.append(f"- works on ORCID: {len(works)}; candidates before cleanup: {len(ok)}")
        for w in ok:
            report_lines.append(
                f"  - `{w['person']}` | {w['year']} | {w['title']} | {w['journal'] or ''} | "
                f"DOI: {w['doi'] or '-'} | galaxy: {'yes' if w['galaxy_related'] else 'no'}"
            )
        for w, reason in skipped[:10]:
            report_lines.append(f"  - (dropped) {w['title']} — {reason}")
        if len(skipped) > 10:
            report_lines.append(f"  - ... and {len(skipped) - 10} more dropped")
        candidates.extend(ok)

    candidates = dedupe_candidates(candidates)
    candidates = drop_preprint_twins(candidates, existing_titles_raw)
    candidates.sort(key=lambda c: (c["name"], -c["year"]))

    out_dir = Path(args.out_dir) if args.out_dir else Path(__file__).resolve().parent / "data"
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "freiburg-candidates.md").write_text("\n".join(report_lines), encoding="utf-8")
    print(f"\nWrote {out_dir / 'freiburg-candidates.md'}")

    entries, missing = [], []
    for c in candidates:
        if c["doi"]:
            bib = bibtex_from_doi(c["doi"])
            time.sleep(0.3)
            if bib:
                entries.append(clean_bibtex_entry(bib))
                continue
            missing.append(c)
        else:
            missing.append(c)
    entries = dedupe_keys(existing_keys, entries)
    bib_text = "\n\n".join(entries).strip()
    if bib_text:
        bib_text += "\n"
    (out_dir / "candidates.bib").write_text(bib_text, encoding="utf-8")

    print(f"== Summary: {len(candidates)} candidates, {len(entries)} with BibTeX, "
          f"{len(missing)} without BibTeX (manual). ==")
    print(f"Wrote {out_dir / 'candidates.bib'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())