"""
Source: "la Caixa" Foundation doctoral fellowships (INPhINIT) — TIER 1.

INPhINIT is an annual *call* (not a continuous job board), so we represent it
as tracked entries whose deadline rolls to the next expected occurrence. These
are expected dates based on past cycles — always verify on the official page.
"""
from __future__ import annotations

import datetime

CALLS = [
    {
        "title": "la Caixa INPhINIT Incoming — doctoral fellowships",
        "desc": "STEM / life sciences at Severo Ochoa / Maria de Maeztu / "
                "Carlos III accredited Spanish centres",
        "month": 2, "day": 4,
        "url": "https://fundacionlacaixa.org/en/doctoral-inphinit-fellowships-incoming",
    },
    {
        "title": "la Caixa INPhINIT Retaining — doctoral fellowships",
        "desc": "All disciplines, for researchers in Spain or Portugal",
        "month": 4, "day": 15,
        "url": "https://fundacionlacaixa.org/en/doctoral-inphinit-fellowships-retaining",
    },
]


def _next_annual(month: int, day: int) -> str:
    today = datetime.date.today()
    d = datetime.date(today.year, month, day)
    if d < today:
        d = datetime.date(today.year + 1, month, day)
    return d.isoformat()


def scrape(verbose: bool = True) -> list[dict]:
    records = []
    for c in CALLS:
        deadline = _next_annual(c["month"], c["day"])
        records.append({
            "source": "la Caixa",
            "id": "lacaixa-" + c["title"].split("—")[0].strip().lower().replace(" ", "-"),
            "title": c["title"],
            "organisation": '"la Caixa" Foundation',
            "host_institution": "Spanish research centres (host of choice)",
            "country": "Spain",
            "number_of_offers": "",
            "research_field": c["desc"],
            "researcher_profile": "First Stage Researcher (R1)",
            "funding_programme": "la Caixa INPhINIT",
            "programme_type": "la Caixa",
            "open_date": "",
            "deadline": deadline,
            "deadline_display": f"{deadline} (expected — verify on official page)",
            "start_date": "",
            "employment_type": "",
            "hours_per_week": "",
            "education_level": "",
            "grant_agreement_number": "",
            "url": c["url"],
            "detail_available": "call",
        })
    if verbose:
        print(f"  la Caixa: {len(records)} tracked INPhINIT call(s)")
    return records
