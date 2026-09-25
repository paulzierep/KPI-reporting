#!/usr/bin/env python3
"""TIaaS (Training Infrastructure as a Service, usegalaxy.eu) events per year.

The public calendar endpoint exposes all TIaaS training events with their
start/end dates (names are intentionally stripped for privacy):

    https://usegalaxy.eu/tiaas/calendar/events.json

Event start dates are grouped by calendar year; training duration in days is
accumulated per year as well.

Usage
-----
    python3 tiaas_stats.py

Writes `data/tiaas_events_per_year.tsv`.
"""

import datetime
import json
import urllib.request
from pathlib import Path

EVENTS_URL = "https://usegalaxy.eu/tiaas/calendar/events.json"


def main():
    out_dir = Path(__file__).resolve().parent / "data"
    out_dir.mkdir(exist_ok=True)

    data = json.loads(
        urllib.request.urlopen(EVENTS_URL, timeout=120).read().decode("utf-8")
    )
    events = data.get("events", data) if isinstance(data, dict) else data

    years = {}
    for e in events:
        y = int(e["start"][:4])
        days = (datetime.date.fromisoformat(e["end"])
                - datetime.date.fromisoformat(e["start"])).days + 1
        years.setdefault(y, [0, 0])
        years[y][0] += 1
        years[y][1] += days

    out = out_dir / "tiaas_events_per_year.tsv"
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("year\tevents\ttraining_days\n")
        for y in sorted(years):
            n, days = years[y]
            fh.write(f"{y}\t{n}\t{days}\n")

    print(f"TIaaS events per year (total {len(events)} since 2018-06-20):")
    for y in sorted(years):
        n, days = years[y]
        print(f"  {y}: {n:>3} events, {days:>5} training days")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()