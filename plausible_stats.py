#!/usr/bin/env python3
"""Fetch usage statistics for Galaxy websites from the EU Plausible instance.

Plausible backend: https://plausible.galaxyproject.eu

Available site ids
------------------
    training.galaxyproject.org   # Galaxy Training Network (GTN)
    usegalaxy.eu                 # UseGalaxy.eu

Requires a Plausible API key (bearer token). Provide it via the environment
variable PLAUSIBLE_API_KEY or the --api-key flag. Ask a UseGalaxy.eu admin to
issue one if you do not have it.

Usage
-----
    python3 plausible_stats.py training.galaxyproject.org 12mo
    python3 plausible_stats.py usegalaxy.eu 2023-01-01,2023-12-31
    PLAUSIBLE_API_KEY=... python3 plausible_stats.py usegalaxy.eu year --metrics pageviews,visitors

Periods follow the Plausible API: 30d, 6mo, 12mo, year, or a comma-separated
custom date range `YYYY-MM-DD,YYYY-MM-DD` (uses period=custom).

API reference: https://plausible.io/docs/stats-api
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_METRICS = ("visitors", "pageviews")
BASE_URL = "https://plausible.galaxyproject.eu/api/v1/stats/aggregate"


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("site_id", help="website domain, e.g. training.galaxyproject.org")
    p.add_argument("period", nargs="?", default="12mo",
                   help="period: 30d, 6mo, 12mo, year, or DATE1,DATE2")
    p.add_argument("--metrics", default=",".join(DEFAULT_METRICS),
                   help="comma-separated metrics (visitors, pageviews, visits, bounce_rate, visit_duration)")
    p.add_argument("--api-key", default=os.environ.get("PLAUSIBLE_API_KEY", ""),
                   help="Plausible API key (default: $PLAUSIBLE_API_KEY)")
    return p.parse_args()


def main():
    args = parse_args()
    if not args.api_key:
        sys.exit("no API key: set PLAUSIBLE_API_KEY or pass --api-key")

    params = {"site_id": args.site_id, "metrics": args.metrics}
    if "," in args.period:
        params.update({"period": "custom", "date": args.period})
    else:
        params["period"] = args.period

    url = BASE_URL + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(
        url, headers={"Authorization": f"Bearer {args.api_key}"}
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.load(resp)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        sys.exit(f"HTTP {exc.code} for {url}\n  {body}")

    result = data.get("results", {})
    print(f"site_id: {args.site_id}\tperiod: {args.period}")
    for metric, value in sorted(result.items()):
        if value is not None:
            val = f"{int(value):,}" if isinstance(value, int) else value
            print(f"{metric}: {val}")


if __name__ == "__main__":
    main()