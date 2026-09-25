#!/usr/bin/env python3
"""Count emails sent from galaxy-no-reply@informatik.uni-freiburg.de per year.

Connects to Gmail over IMAP (imap.gmail.com:993) and uses Gmail's X-GM-RAW
search extension to run a full Gmail query per calendar year, e.g.:

    from:galaxy-no-reply@informatik.uni-freiburg.de
    after:2022/12/31 before:2024/1/1

The search runs over "[Gmail]/All Mail" so sent + received + archived messages
are all covered. Gmail search after:/before: is based on message date, so the
counts are approximately calendar-year send dates.

Credentials
-----------
Requires a Google "App Password" (Google Account > Security > App passwords;
needs 2-Step Verification enabled) for the account that owns the mailbox.

Provide them via a config file or environment variables:

    export GMAIL_USER=you@gmail.com
    export GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx

or ~/.config/galaxy-kpi/gmail.ini:
    [gmail]
    user = you@gmail.com
    app_password = xxxx xxxx xxxx xxxx

Usage
-----
    python3 gmail_galaxy_no_reply.py          # 2023, 2024, 2025
    python3 gmail_galaxy_no_reply.py 2024     # single year
"""

import configparser
import email
import email.utils
import imaplib
import os
import re
import shlex
import sys
from pathlib import Path

HOST = "imap.gmail.com"
SENDER = "galaxy-no-reply@informatik.uni-freiburg.de"
DEFAULT_YEARS = (2023, 2024, 2025)
CONFIG_PATH = Path.home() / ".config" / "galaxy-kpi" / "gmail.ini"
CHUNK = 100


def find_all_mail_folder(conn):
    """Return the Gmail 'All Mail' folder name, locale-independent."""
    typ, data = conn.list()
    if typ != "OK":
        sys.exit("could not list mailboxes")
    candidates = []
    for line in data:
        entries = line.decode().split(' "')
        if len(entries) < 2:
            continue
        attrs = entries[0].lower()
        name = entries[-1]
        if "\\all" in attrs:
            candidates.append(name)
    if candidates:
        return candidates[0].strip('"')
    for fallback in ("[Gmail]/All Mail", "[Google Mail]/All Mail", "All Mail"):
        if fallback in str(data):
            return fallback
    sys.exit("could not find the All Mail folder")


def credentials():
    user = os.environ.get("GMAIL_USER") or ""
    password = os.environ.get("GMAIL_APP_PASSWORD") or ""
    if not (user and password) and CONFIG_PATH.exists():
        cfg = configparser.ConfigParser()
        cfg.read(CONFIG_PATH)
        user = user or cfg.get("gmail", "user", fallback="")
        password = password or cfg.get("gmail", "app_password", fallback="")
    if not (user and password):
        sys.exit(
            "no credentials: set GMAIL_USER + GMAIL_APP_PASSWORD (env) or "
            f"create {CONFIG_PATH} (user + app_password under [gmail])"
        )
    return user, password.replace(" ", "")


def gmail_query(sender, year):
    """return Gmail search query for mails from `sender` in `year`."""
    return (
        f"from:{sender} after:{year - 1}/12/31 before:{year + 1}/01/01"
    )


def search_year(conn, query):
    """Return the list of UIDs matching `query` (or None on error)."""
    typ, data = conn.uid("search", None, f'(X-GM-RAW "{query}")')
    if typ != "OK":
        return None
    return data[0].split() if data and data[0] else []


def fetch_mail_info(conn, uids):
    """Fetch metadata per UID -> list of dicts (no message content stored).

    Fields: date, time, day_of_week, size, labels, mime, kind.
    """
    rows = []
    for i in range(0, len(uids), CHUNK):
        batch = b",".join(uids[i:i + CHUNK])
        typ, data = conn.uid(
            "fetch",
            batch,
            "(RFC822.SIZE X-GM-LABELS "
            "BODY.PEEK[HEADER.FIELDS (DATE SUBJECT CONTENT-TYPE)])",
        )
        if typ != "OK":
            continue
        for resp in data:
            if not isinstance(resp, tuple):
                continue
            text = resp[0].decode("utf-8", "replace")
            headers = resp[1].decode("utf-8", "replace")
            labels = []
            match = re.search(r"X-GM-LABELS \((.*?)\)", resp[0].decode("ascii", "replace"))
            if match:
                try:
                    labels = shlex.split(match.group(1).replace('"', '\\"'))
                except ValueError:
                    labels = match.group(1).split()
            size = re.search(r"RFC822\.SIZE (\d+)", text)
            mime = "other"
            date = subject = ctype = None
            for line in headers.splitlines():
                low = line.lower()
                if low.startswith("date:") and date is None:
                    try:
                        dt = email.utils.parsedate_to_datetime(line[5:].strip())
                    except (TypeError, ValueError):
                        dt = None
                    date = dt
                elif low.startswith("subject:") and subject is None:
                    subject = line[8:].strip()
                elif low.startswith("content-type:") and ctype is None:
                    ctype = line[13:].strip()
            if ctype:
                mime = ctype.split(";")[0].strip().lower()
            if date is None:
                continue
            rows.append(
                {
                    "date": date.date().isoformat(),
                    "time": date.strftime("%H:%M"),
                    "day_of_week": date.strftime("%a"),
                    "size": int(size.group(1)) if size else "",
                    "labels": "|".join(labels),
                    "mime": mime,
                    "kind": subject_kind(subject),
                }
            )
    return rows


def subject_kind(subject):
    """Coarse category of the email subject (no content/user info stored)."""
    s = (subject or "").lower()
    if s.startswith("galaxy tool error report"):
        return "error_report"
    if "tiaas" in s:
        return "tiaas_request"
    return "other"


def main():
    years = [int(a) for a in sys.argv[1:] if a.isdigit()] or list(DEFAULT_YEARS)
    user, password = credentials()

    print(f"connecting to {HOST} as {user} ...")
    conn = imaplib.IMAP4_SSL(HOST)
    try:
        conn.login(user, password)
    except imaplib.IMAP4.error as exc:
        sys.exit(f"login failed: {exc}")
    folder = find_all_mail_folder(conn)
    typ, _ = conn.select('"' + folder + '"', readonly=True)
    if typ != "OK":
        sys.exit(f"failed to select All Mail: {typ}")

    results = {}
    uid_by_year = {}
    for year in years:
        query = gmail_query(SENDER, year)
        uids = search_year(conn, query)
        if uids is None:
            sys.exit(f"X-GM-RAW search failed for {year}")
        uid_by_year[year] = uids
        results[year] = len(uids)
        print(f"galaxy-no-reply emails {year}: {len(uids):,}")

    csv_path = Path(__file__).resolve().parent / "data" / "galaxy_no_reply_maillist.csv"
    csv_path.parent.mkdir(exist_ok=True)
    dates_by_year = {}
    kinds_by_year = {}
    with open(csv_path, "w", encoding="utf-8") as fh:
        fh.write("year,date,time,day_of_week,size,category,labels,mime\n")
        for year in years:
            print(f"  fetching metadata for {year} ({len(uid_by_year[year]):,} mails) ...")
            rows = fetch_mail_info(conn, uid_by_year[year])
            dates_by_year[year] = [r["date"] for r in rows]
            kinds_by_year[year] = {}
            for r in rows:
                kinds_by_year[year][r["kind"]] = kinds_by_year[year].get(r["kind"], 0) + 1
                fh.write(
                    f"{year},{r['date']},{r['time']},{r['day_of_week']},"
                    f"{r['size']},{r['kind']},{r['labels'].replace(chr(92), '')},"
                    f"{r['mime']}\n"
                )
    print(f"wrote {csv_path} (date + coarse category, no content/user info)")

    conn.logout()

    out = Path(__file__).resolve().parent / "data" / "galaxy_no_reply_emails.tsv"
    out.parent.mkdir(exist_ok=True)
    kinds_out = Path(__file__).resolve().parent / "data" / "galaxy_no_reply_kinds.tsv"
    with open(out, "w", encoding="utf-8") as fh, open(kinds_out, "w", encoding="utf-8") as kf:
        fh.write("year\tcount\n")
        kf.write("year\tcategory\tcount\n")
        for year in sorted(results):
            from_dates = dates_by_year.get(year, [])
            fh.write(f"{year}\t{len(from_dates)}\n")
            flag = "" if len(from_dates) == results[year] else f"  (search said {results[year]})"
            print(f"galaxy-no-reply emails {year} (from Date header): {len(from_dates):,}{flag}")
            for kind, n in sorted(kinds_by_year.get(year, {}).items()):
                kf.write(f"{year}\t{kind}\t{n}\n")
                print(f"    {kind}: {n:,}")
    print(f"wrote {out}")
    print(f"wrote {kinds_out}")


if __name__ == "__main__":
    main()