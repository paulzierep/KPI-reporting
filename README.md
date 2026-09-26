# galaxy-KPI

KPIs for the Galaxy project. Each metric has a small script plus the
resulting numbers in `data/`.

- 1 – [Bioconda package downloads](#1-bioconda-package-downloads)
- 2 – [GTN / EU usage stats (Plausible)](#2-gtn--eu-usage-stats-plausible)
- 3 – [Galaxy no-reply notification emails (Gmail)](#3-galaxy-no-reply-notification-emails-gmail)
- 4 – [Galaxy Help forum — usegalaxy.eu support topics](#4-galaxy-help-forum--usegalaxyeu-support-topics)
- 5 – [Combined support KPIs](#5-combined-support-kpis)
- 6 – [Citation counts for Galaxy papers](#6-citation-counts-for-galaxy-papers)
- 7 – [Google Scholar citation counts (partial)](#7-google-scholar-citation-counts-partial)
- 8 – [Freiburg Galaxy Team publications](#8-freiburg-galaxy-team-publications)

## 1. Bioconda package downloads

Total downloads of the `bioconda` conda channel per calendar year.

Data source: [bioconda-stats](https://github.com/bioconda/bioconda-stats)
(`data` branch). The repo tracks the daily all-time cumulative download total
(`package-downloads/anaconda.org/bioconda/channel.tsv`, one row per day). A
calendar year's downloads telescope to:

```
downloads(Y) = channel_total(Dec 31, Y) - channel_total(Dec 31, Y-1)
```

### Run

```bash
python3 bioconda_downloads.py          # 2023, 2024, 2025
python3 bioconda_downloads.py 2024     # single year
```

Needs network access. Current numbers (`data/bioconda_yearly_downloads.tsv`):

| year | downloads  |
|------|------------|
| 2023 |  89,892,900 |
| 2024 |  77,371,784 |
| 2025 | 112,308,105 |

### Tool update stats

`bioconda_tool_updates.py` compares the per-version files shipped in each
date snapshot (`versions/<pkg>.tsv`, one cumulative download total per
version). Any version whose key is new at the end of year Y relative to
Y-1 counts as a **new version released + downloaded in Y**:

```bash
python3 bioconda_tool_updates.py
```

| year | packages with new version | new versions released |
|------|--------------------------:|----------------------:|
| 2023 | 4,359 | 9,845 |
| 2024 | 4,213 | 7,660 |
| 2025 | 2,748 | 6,509 |

Column units: **new versions released** represents the number of individual
version bumps that appeared in the year's snapshots — i.e. versions actually
released and downloaded for the first time in that year, summed over all
packages. **Packages with new version** counts each distinct package only once
per year, regardless of how many of its versions shipped (snakemake alone
released 70 new versions in 2024).

Most frequently updated package in each year: pybiolib (77/92/91 new versions).
Watchlist highlights (full data `data/bioconda_new_versions.tsv`):

- 2023: multiqc 1.14–1.19, samtools/bcftools 1.17/1.18/1.19, fastp 0.23.3–0.23.4, star 2.7.11a
- 2024: snakemake 70 new versions (8.x), multiqc 1.20–1.26, fastp 0.24.0, samtools 1.19.1–1.21
- 2025: fastp 0.24.x–0.26.0 and 1.0.0/1.0.1, multiqc 1.27–1.33, samtools 1.22–1.23, snakemake 9.x

### More bioconda KPIs

`bioconda_stats.py` reuses the same snapshots to derive further easy numbers
(`data/bioconda_*.tsv`): per-platform split, top downloaded packages, active /
new package counts, plus a Galaxy-tools watchlist.

```bash
python3 bioconda_stats.py
```

Active packages (high-level downloads = anything) and packages new to the
channel per year:

| year | active packages | new packages |
|------|----------------:|-------------:|
| 2023 | 10,361 | 700 |
| 2024 | 11,019 | 660 |
| 2025 | 11,779 | 758 |

Top-3 downloaded packages per year:

| year | #1 | #2 | #3 |
|------|----|----|----|
| 2023 | htslib 1.10M | samtools 1.10M | pysam 0.58M |
| 2024 | samtools 0.78M | htslib 0.74M | pysam 0.48M |
| 2025 | pysam 4.00M | samtools 1.95M | harpy 1.85M |

Platform / subdir split (only 2025: the channel.tsv boundary rows carry
per-subdir columns only from 2024-12-31 onwards; full table in
`data/bioconda_platforms.tsv`):

| subdir | 2025 downloads | share |
|--------|---------------:|------:|
| linux-64 | 48,792,701 | 43.4 % |
| noarch | 35,856,072 | 31.9 % |
| osx-64 | 23,066,493 | 20.5 % |
| linux-aarch64 | 3,323,548 | 3.0 % |
| osx-arm64 | 1,269,291 | 1.1 % |

## 2. GTN / EU usage stats (Plausible)

Usage statistics (visitors, pageviews) for the Galaxy Training Network and
UseGalaxy.eu are tracked in the EU Plausible instance:

- GTN:  https://plausible.galaxyproject.eu/training.galaxyproject.org
- EU:   https://plausible.galaxyproject.eu/usegalaxy.eu

The [Plausible Stats API](https://plausible.io/docs/stats-api) requires an API
key (bearer token). Ask a UseGalaxy.eu admin for one if you do not have it.

### With the script

```bash
python3 plausible_stats.py training.galaxyproject.org 12mo
python3 plausible_stats.py usegalaxy.eu 2023-01-01,2023-12-31
PLAUSIBLE_API_KEY=... python3 plausible_stats.py usegalaxy.eu year
```

Periods: `30d`, `6mo`, `12mo`, `year`, or a custom range `YYYY-MM-DD,YYYY-MM-DD`.
Metrics: `visitors,pageviews,visits,bounce_rate,visit_duration` (change with `--metrics`).

### Directly with curl

```bash
# GTN pageviews over the last 12 months
curl "https://plausible.galaxyproject.eu/api/v1/stats/aggregate \
  ?site_id=training.galaxyproject.org&period=12mo&metrics=pageviews,visitors" \
  -H "Authorization: Bearer $PLAUSIBLE_API_KEY"

# UseGalaxy.eu pageviews in 2023
curl "https://plausible.galaxyproject.eu/api/v1/stats/aggregate \
  ?site_id=usegalaxy.eu&period=custom&date=2023-01-01,2023-12-31&metrics=pageviews" \
  -H "Authorization: Bearer $PLAUSIBLE_API_KEY"
```

### GTN content stats from the archive

The GTN freezes a snapshot of the whole site under
`https://training.galaxyproject.org/archive/<YYYY-MM-DD>/`, and from
2023-06 onwards each snapshot ships a stats page. The year-start snapshots
(2024-01-01, 2025-01-01, 2026-01-01) give exact year boundaries, so 2024 and
2025 growth is exact; 2023 has no baseline (2023-01-01 snapshots have no stats
page). `gtn_archive_stats.py` scrapes them:

```bash
python3 gtn_archive_stats.py
```

Year-end content counts (`data/gtn_archive_stats.tsv`):

| end of year | tutorials | topics | learning paths | FAQs | workflows | videos (hours) | news posts | contributors |
|-------------|----------:|-------:|---------------:|-----:|----------:|---------------:|-----------:|-------------:|
| 2023 | 383 | 29 | – | 411 | – | – | – | 317 |
| 2024 | 441 | 33 | 20 | 471 | – | 200 (135.0 h) | 102 | 437 |
| 2025 | 498 | 35 | 28 | 489 | 343 | 214 (147.5 h) | 123 | 510 |
| 2026 (current) | 530 | 35 | 28 | 549 | 366 | 214 (150.8 h) | 127 | 541 |

Added per year (`data/gtn_archive_new_per_year.tsv`):

| year | tutorials | topics | FAQs | videos | news posts | contributors |
|------|----------:|-------:|-----:|-------:|-----------:|-------------:|
| 2024 | +58 | +4 | +60 | – | – | +120 |
| 2025 | +57 | +2 | +18 | +14 | +21 | +73 |

(`–` = baseline snapshot did not report that metric.)

## 3. Galaxy no-reply notification emails (Gmail)

Counts of emails sent from `galaxy-no-reply@informatik.uni-freiburg.de`
(Galaxy Freiburg server notifications) in 2023/2024/2025, by querying the
mailbox over IMAP (`imap.gmail.com`, `[Gmail]/All Mail`) with Gmail's
`X-GM-RAW` search extension, e.g. `from:galaxy-no-reply@informatik.uni-freiburg.de after:2022/12/31 before:2024/1/1`.

### Prerequisites

1. Enable 2-Step Verification on the Google account.
2. Create an App Password: Google Account → Security → App passwords.

### Run

```bash
export GMAIL_USER=you@gmail.com
export GMAIL_APP_PASSWORD='xxxx xxxx xxxx xxxx'

python3 gmail_galaxy_no_reply.py          # 2023, 2024, 2025
python3 gmail_galaxy_no_reply.py 2024     # single year
```

Alternatively create `~/.config/galaxy-kpi/gmail.ini`:

```ini
[gmail]
user = you@gmail.com
app_password = xxxx xxxx xxxx xxxx
```

Note: the app password is never committed (see `.gitignore`). Counts are
written to `data/galaxy_no_reply_emails.tsv`.

Results (from `paul.zierep@gmail.com`, querying `[Google Mail]/All Mail`):

| year | emails from galaxy-no-reply |
|------|-----------------------------|
| 2023 | 1,234 |
| 2024 | 1,328 |
| 2025 | 1,432 |

Breakdown by mail type (`data/galaxy_no_reply_kinds.tsv`, categories derived
from the subject without storing names/content):

| year | error reports | TIaaS requests | other |
|------|--------------:|---------------:|------:|
| 2023 | 1,160 | 74 | 0 |
| 2024 | 1,250 | 78 | 0 |
| 2025 | 1,338 | 93 | 1 |

For verification, every run also dumps the full mail list to
`data/galaxy_no_reply_maillist.csv` — one row per email, metadata only (no
sender, recipient, subject, or content):

`year,date,time,day_of_week,size,category,labels,mime`

e.g. `2023,2023-01-12,10:53,Thu,11173,error_report,"Important"|"Inbox"|"Privat"|galaxy,multipart/alternative`

The counts above are recomputed from the fetched Date headers, so they can be
cross-checked against the CSV (3,994 rows) and compared with a colleague's
numbers.

## 4. Galaxy Help forum — usegalaxy.eu support topics

All topics in the `usegalaxy.eu support` category of the Galaxy Help forum
(https://help.galaxyproject.org, Discourse), fetched via its public JSON API.

### Run

```bash
python3 galaxy_help_topics.py
```

Writes `data/galaxy_help_usegalaxy_eu_topics.csv` (topic id, created/last-post
date, title, post counts) and per-year counts to
`data/galaxy_help_usegalaxy_eu_topics_by_year.tsv`.

Topics created per year (total topics in category: 1,342):

| year | new topics |
|------|-----------:|
| 2023 | 200 |
| 2024 | 216 |
| 2025 | 223 |

## 5. Combined support KPIs

`combine_support_kpis.py` merges the mail breakdown
(`galaxy_no_reply_kinds.tsv`) with the help-forum topics
(`galaxy_help_usegalaxy_eu_topics_by_year.tsv`) into one table:

```bash
python3 combine_support_kpis.py    # -> data/combined_support_kpis.tsv
```

| year | error-report mails | TIaaS mails | help topics | total |
|------|-------------------:|------------:|------------:|------:|
| 2023 | 1,160 | 74 | 200 | 1,434 |
| 2024 | 1,250 | 78 | 216 | 1,544 |
| 2025 | 1,338 | 93 | 223 | 1,654 |

### TIaaS training events

`tiaas_stats.py` reads the public usegalaxy.eu TIaaS calendar
(`/tiaas/calendar/events.json`, event names stripped for privacy) and the
database dump (`/tiaas/numbers.csv`, per-event attendance) and counts training
events by start year, the training days they cover, and attendees:

```bash
python3 tiaas_stats.py      # -> data/tiaas_events_per_year.tsv
```

| year | training events | training days | people trained |
|------|----------------:|--------------:|---------------:|
| 2023 | 85 | 1,030 | 3,300 |
| 2024 | 72 | 937 | 2,628 |
| 2025 | 90 | 699 | 3,063 |

Since the service started (2018-06-20) 636 events have trained 24,749 people
over 8,695 days of compute (matches the `/tiaas/stats` lifetime figures). Note:
TIaaS request mails (74/78/93) are applications, not accepted/running events.

## 6. Citation counts for Galaxy papers

Citation numbers for the Galaxy NAR update papers, collected from Crossref
(`is-referenced-by-count`), OpenAlex (`cited_by_count` + full citing-work
list), and optionally Semantic Scholar. No API keys needed.

### Run

```bash
python3 citations.py                        # all tracked Galaxy papers
python3 citations.py -d 10.1093/nar/gkae410 # add any DOI
python3 citations.py -d 10.1101/gr.4086505 -d 10.1186/gb-2010-11-8-r86  # the other canon papers
python3 citations.py --semanticscholar      # also query Semantic Scholar
```

Writes `data/citations_summary.tsv`, `data/citations_by_year.tsv`, and one
`data/citations_<doi>.tsv` per paper (all citing works with year/title/venue/DOI).

Results (retrieved 2026-09-24/25):

| paper | DOI | Crossref | OpenAlex |
|---|---|---|---|
| Galaxy 2005 (Genome Research) | 10.1101/gr.4086505 | 1,776 | 2,098 |
| Using Galaxy 2007 (Curr. Protoc. Bioinf.) | 10.1002/0471250953.bi1005s19 | 61 | 146 |
| Galaxy 2010 (Genome Biology) | 10.1186/gb-2010-11-8-r86 | 2,991 | 3,572 |
| Galaxy 2010 (Curr. Protoc. Mol. Biol.) | 10.1002/0471142727.mb1910s89 | 720 | 1,468 |
| Galaxy 2016 update (NAR 44, W3-W10) | 10.1093/nar/gkw343 | 1,863 | 2,314 |
| Galaxy 2018 update (NAR 46, W537-W544) | 10.1093/nar/gky379 | 3,675 | 3,838 |
| Galaxy 2022 update (NAR 50, W345-W351) | 10.1093/nar/gkac247 | 1,030 | 1,371 |
| Galaxy 2024 update (NAR 52, W83-W94) | 10.1093/nar/gkae410 | 1,038 | 965 |
| Galaxy 2026 update (NAR 54, W105-W116) | 10.1093/nar/gkag469 | 24 | 15 |

### Unique citations across all nine Galaxy papers

A citing work may cite several Galaxy papers, so `unique_citations.py`
deduplicates the citing DOIs across all `data/citations_*.tsv` lists:

```bash
python3 unique_citations.py            # 2023-2025
python3 unique_citations.py 2024       # single year
```

Unique citing works (OpenAlex) for 2023-2025
(`data/unique_citations_2023-2025.tsv`):

| year | unique citing works |
|------|--------------------:|
| 2023 | 1,118 |
| 2024 | 1,150 |
| 2025 | 1,220 |
| **total** | **3,488** |

### Publications citing UseGalaxy.eu

`eu_citations.py` downloads `citations-eu.bib` from the Galaxy Hub — the
bibliography of publications citing the European Galaxy server, maintained in
the Galaxy Publications Zotero group
(https://www.zotero.org/groups/1732893/items, tag `>UseGalaxy.eu`; both
sources contain the same 1,731 entries) — and counts publications by year:

```bash
python3 eu_citations.py        # -> data/eu_citations_by_year.tsv
```

Total: 1,731 publications citing UseGalaxy.eu.

| year | publications |
|------|-------------:|
| 2023 | 282 |
| 2024 | 359 |
| 2025 | 387 |

## 7. Google Scholar citation counts (partial)

`google_scholar_citations.py` scrapes Google Scholar's "Cited by N" for each
major Galaxy paper. Scholar has **no public API**, so this does one HTML title
query per paper; Google aggressively rate-limits (CAPTCHA), so the script
**resumes** previously collected DOIs (`data/google_scholar_citations.tsv`)
and should be re-run after a cool-down to fill gaps:

```bash
python3 google_scholar_citations.py   # skips DOIs already in the summary
```

| Galaxy paper | Scholar | OpenAlex | Crossref |
|--------------|--------:|---------:|---------:|
| 2005 Genome Research | 2,789 | 2,098 | 1,776 |
| Using Galaxy 2007 (Curr. Protoc. Bioinf.) | 159 | 146 | 61 |
| 2010 Genome Biology | 4,507 | 3,572 | 2,991 |
| 2010 Curr. Protoc. Mol. Biol. | 1,915 | 1,468 | 720 |
| 2022 update (NAR 50) | **pending (CAPTCHA)** | 1,407 | 1,030 |
| 2024 update (NAR 52) | 858 | 966 | 1,038 |
| 2026 update (NAR 54) | **pending (CAPTCHA)** | 15 | 24 |

Notes: Scholar counts include preprint/duplicate records and differ in
real-time, so absolute numbers are not directly comparable across sources.
The full per-year citing list harvest (`--citing-list`) is impractical for
papers with thousands of citations (10/page -> hundreds of requests,
guaranteed CAPTCHA); use OpenAlex (`citations.py` + `unique_citations.py`)
for the year-by-year analysis.

## 8. Freiburg Galaxy Team publications

`freiburg-publications/freiburg_publications.py` mines the ORCID records of
everyone listed under `freiburg` in the Galaxy Hub `content/people/people.yaml`
to find recent publications not yet in the Freiburg bibliography
(`content/freiburg/citations/freiburg.bib`). Join year = earliest strictly
Galaxy-related work; preprints whose journal version is already known are
dropped. See [freiburg-publications/README.md](freiburg-publications/README.md)
for full documentation.

```bash
python3 freiburg-publications/freiburg_publications.py
```

Outputs `freiburg-publications/data/candidates.bib` (new BibTeX entries) and
`freiburg-publications/data/freiburg-candidates.md` (per-person report).