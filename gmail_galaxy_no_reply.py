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
import imaplib
import os
import sys
from pathlib import Path

HOST = "imap.gmail.com"
SENDER = "galaxy-no-reply@informatik.uni-freiburg.de"
DEFAULT_YEARS = (2023, 2024, 2025)
CONFIG_PATH = Path.home() / ".config" / "galaxy-kpi" / "gmail.ini"


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


def count_year(conn, query):
    typ, data = conn.uid("search", None, f'(X-GM-RAW "{query}")')
    if typ != "OK":
        return None
    ids = data[0].split()
    return len(ids)


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
    for year in years:
        query = gmail_query(SENDER, year)
        n = count_year(conn, query)
        if n is None:
            sys.exit(f"X-GM-RAW search failed for {year}")
        results[year] = n
        print(f"galaxy-no-reply emails {year}: {n:,}")

    conn.logout()

    out = Path(__file__).resolve().parent / "data" / "galaxy_no_reply_emails.tsv"
    out.parent.mkdir(exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("year\tcount\n")
        for year, n in sorted(results.items()):
            fh.write(f"{year}\t{n}\n")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()