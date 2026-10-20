"""
Source: VHIO (Vall d'Hebron Institute of Oncology) — Teamtailor job board.

Scrapes https://jobs.vhio.net and returns records in the common schema used by
run.py. The board is small; we fetch the list then each detail page (JSON-LD
JobPosting + a few body fields). "Scholarship" listings (predoctoral / PhD /
doctoral / fellowship) are flagged so the main report can keep just those.
"""
from __future__ import annotations

import json
import re
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup

import config

LIST_URL = "https://jobs.vhio.net/jobs"
SITE = "https://jobs.vhio.net"

# Title/description keywords that mark a listing as a scholarship/PhD.
SCHOLARSHIP_KEYWORDS = [
    "predoctoral", "pre-doctoral", "phd", "ph.d", "doctoral", "doctorate",
    "fellowship", "scholarship", "beca", "estudiante de doctorado",
    "postdoctoral", "post-doctoral", "fpi", "la caixa",
]


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": config.USER_AGENT, "Accept-Language": "en"})
    return s


def _get(s, url):
    for attempt in range(1, config.MAX_RETRIES + 1):
        try:
            return s.get(url, timeout=config.REQUEST_TIMEOUT)
        except requests.RequestException:
            time.sleep(min(2 ** attempt, 8))
    return None


def _job_posting(soup):
    for b in soup.select('script[type="application/ld+json"]'):
        try:
            data = json.loads(b.string or b.get_text())
        except (json.JSONDecodeError, TypeError):
            continue
        stack = [data]
        while stack:
            o = stack.pop()
            if isinstance(o, dict):
                if o.get("@type") == "JobPosting":
                    return o
                stack.extend(o.values())
            elif isinstance(o, list):
                stack.extend(o)
    return None


def _country(job):
    loc = job.get("jobLocation")
    if isinstance(loc, list):
        loc = loc[0] if loc else {}
    if isinstance(loc, dict):
        addr = loc.get("address", {})
        if isinstance(addr, dict):
            return addr.get("addressCountry", "") or addr.get("addressLocality", "")
    return ""


def _clean(t):
    return re.sub(r"\s+", " ", (t or "")).strip()


def is_scholarship(title: str, text: str) -> bool:
    blob = f"{title}\n{text}".lower()
    return any(kw in blob for kw in SCHOLARSHIP_KEYWORDS)


def scrape(scholarships_only: bool = True, verbose: bool = True) -> list[dict]:
    s = _session()
    r = _get(s, LIST_URL)
    if not r or r.status_code != 200:
        if verbose:
            print("  VHIO list unavailable")
        return []
    soup = BeautifulSoup(r.content, "html.parser")
    links = sorted({
        a["href"] for a in soup.select('a[href*="/jobs/"]')
        if re.search(r"/jobs/\d+", a.get("href", ""))
    })
    if verbose:
        print(f"  VHIO: {len(links)} listings on board")

    records = []
    for href in links:
        url = href if href.startswith("http") else SITE + href
        rd = _get(s, url)
        if not rd or rd.status_code != 200:
            continue
        ds = BeautifulSoup(rd.content, "html.parser")
        job = _job_posting(ds) or {}
        body = ds.get_text("\n", strip=True)
        title = _clean(job.get("title")) or _clean(
            (ds.find("h1").get_text() if ds.find("h1") else ""))

        if scholarships_only and not is_scholarship(title, body):
            time.sleep(config.REQUEST_DELAY_SECONDS)
            continue

        # open date
        open_date = ""
        if job.get("datePosted"):
            try:
                open_date = datetime.fromisoformat(
                    job["datePosted"].replace("Z", "+00:00")).date().isoformat()
            except ValueError:
                pass
        # deadline: Teamtailor (English board) shows an "Application deadline:" line
        dl_m = re.search(r"Application deadline\s*:?\s*\n?\s*([^\n]{1,40})", body, re.I)
        deadline_display = _clean(dl_m.group(1)) if dl_m else ""
        # Normalise an explicit date (ISO or dd/mm/yyyy) to ISO; else keep text.
        deadline = ""
        iso = re.search(r"(\d{4}-\d{2}-\d{2})", deadline_display)
        dmy = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", deadline_display)
        if iso:
            deadline = iso.group(1)
        elif dmy:
            dd, mm, yy = dmy.groups()
            deadline = f"{yy}-{int(mm):02d}-{int(dd):02d}"

        jid = re.search(r"/jobs/(\d+)", url)
        records.append({
            "source": "VHIO",
            "id": f"vhio-{jid.group(1) if jid else title[:12]}",
            "title": title,
            "organisation": "VHIO (Vall d'Hebron Institute of Oncology)",
            "host_institution": "VHIO",
            "country": "Spain",
            "number_of_offers": "",
            "research_field": "Cancer / oncology",
            "researcher_profile": "",
            "funding_programme": "",
            "programme_type": "VHIO",
            "open_date": open_date,
            "deadline": deadline,
            "deadline_display": deadline_display,
            "start_date": "",
            "employment_type": _clean(str(job.get("employmentType", ""))),
            "hours_per_week": "",
            "education_level": "",
            "grant_agreement_number": "",
            "url": url,
            "detail_available": "yes" if job else "partial",
        })
        time.sleep(config.REQUEST_DELAY_SECONDS)

    if verbose:
        print(f"  VHIO: kept {len(records)} scholarship/PhD listing(s)")
    return records


if __name__ == "__main__":
    for r in scrape(scholarships_only=False):
        print(r["id"], "|", r["title"][:60], "|", r["deadline_display"])
