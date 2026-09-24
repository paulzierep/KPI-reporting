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