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

Results (retrieved 2026-09-24):

| paper | DOI | Crossref | OpenAlex | Semantic Scholar |
|---|---|---|---|---|
| 2026 update (NAR 54, W105-W116) | 10.1093/nar/gkag469 | 24 | 15 | 15 |
| 2024 update (NAR 52, W83-W94) | 10.1093/nar/gkae410 | 1,038 | 966 | 846 |
| 2022 update (NAR 50, W345-W351) | 10.1093/nar/gkac247 | 1,030 | 1,407 | 652 |

Citations by year (OpenAlex): the 2024 update went 88 (2024) → 452 (2025) →
425 (2026 so far); the 2022 update peaked at 479 (2024).