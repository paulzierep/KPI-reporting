# galaxy-KPI

KPIs for the Galaxy project. Each metric has a small script plus the
resulting numbers in `data/`.

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

## 4. Citation counts for Galaxy papers

Citation numbers for the Galaxy NAR update papers, collected from Crossref
(`is-referenced-by-count`), OpenAlex (`cited_by_count` + full citing-work
list), and optionally Semantic Scholar. No API keys needed.

### Run

```bash
python3 citations.py                        # both Galaxy NAR papers
python3 citations.py -d 10.1093/nar/gkae410 # add any DOI
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

## 5. Galaxy Help forum — usegalaxy.eu support topics

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

## 6. Combined support KPIs

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