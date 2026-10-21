"""
Annual-deadlines status.

The annual_deadlines.csv holds curated *expected* windows for recurring
schemes. On every run we compute an estimated open/upcoming status for each
scheme from today's date (no scraping — so it never breaks). This answers
"which recurring schemes should be open right now?" each week.

Status is an ESTIMATE from past cycles, not a live confirmation.
"""
from __future__ import annotations

import csv
import datetime
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(HERE, "..", "data", "annual_deadlines.csv")

_MONTHS = {
    "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3,
    "april": 4, "apr": 4, "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7,
    "august": 8, "aug": 8, "september": 9, "sep": 9, "sept": 9, "october": 10,
    "oct": 10, "november": 11, "nov": 11, "december": 12, "dec": 12,
}


def _months(text: str) -> list[int]:
    found = []
    for m in re.findall(r"[a-zA-Z]+", text or ""):
        n = _MONTHS.get(m.lower())
        if n and n not in found:
            found.append(n)
    return found


def _next_occurrence(month: int, day: int = 15) -> datetime.date:
    today = datetime.date.today()
    try:
        d = datetime.date(today.year, month, min(day, 28))
    except ValueError:
        d = datetime.date(today.year, month, 28)
    if d < today:
        d = datetime.date(today.year + 1, month, min(day, 28))
    return d


def compute_status(opens: str, deadline: str) -> tuple[str, str]:
    """Return (status_key, human_label)."""
    o, d = (opens or "").lower(), (deadline or "").lower()
    # Several fixed deadlines a year (e.g. Boehringer 1 Feb/Jun/Oct) ~ always open.
    if "rolling" in o or len(re.findall(r"\d{1,2}\s*(?:feb|jun|oct|mar|sep|apr|jan|may|jul|aug|nov|dec)", d)) >= 2 or d.count("/") >= 2:
        return "rolling", "Rolling — several deadlines per year (usually open)"
    if "varies" in o or "varies" in d or not _months(d):
        return "check", "Varies — check the official page"

    ded_months = _months(d)
    open_months = _months(o)
    today = datetime.date.today()

    # Soonest upcoming deadline across cycles.
    next_ded = min(_next_occurrence(m) for m in ded_months)
    # Window start: the open month landing before next_ded, else ~2.5 months prior.
    starts = []
    for m in (open_months or []):
        cand = datetime.date(next_ded.year, m, 1)
        if cand > next_ded:
            cand = datetime.date(next_ded.year - 1, m, 1)
        starts.append(cand)
    open_date = max([s for s in starts if s <= next_ded], default=None)
    if open_date is None:
        open_date = next_ded - datetime.timedelta(days=75)

    if open_date <= today <= next_ded:
        return "open", f"Likely open now — deadline ~{next_ded:%b %d}"
    if today < open_date:
        return "upcoming", f"Opens ~{open_date:%b} (deadline ~{next_ded:%b})"
    return "upcoming", f"Next cycle opens ~{open_date:%b}"


def load(verbose: bool = False) -> list[dict]:
    if not os.path.exists(CSV_PATH):
        return []
    rows = []
    with open(CSV_PATH, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            key, label = compute_status(r.get("typical_opens", ""), r.get("typical_deadline", ""))
            r["status"] = key
            r["status_label"] = label
            rows.append(r)
    # Open first, then upcoming, then rolling/check.
    order = {"open": 0, "rolling": 1, "upcoming": 2, "check": 3}
    rows.sort(key=lambda r: order.get(r["status"], 9))
    if verbose:
        n_open = sum(1 for r in rows if r["status"] == "open")
        print(f"  annual deadlines: {len(rows)} schemes, {n_open} estimated open now")
    return rows


if __name__ == "__main__":
    for r in load():
        print(f"  [{r['status']:8}] {r['scheme'][:40]:40} {r['status_label']}")
