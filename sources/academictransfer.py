"""
Source: AcademicTransfer (Netherlands) — TIER 2.

Uses the public JSON API (api.academictransfer.com). The site is a Nuxt SPA
whose public read-only access token is embedded in the page payload; we extract
it live each run (so it survives token rotation) rather than hard-coding it.

Filters to PhD vacancies (function_types=9) in the life-science fields
(keyword match on the title, consistent with the rest of the tool).
"""
from __future__ import annotations

import json
import re
import time
from datetime import datetime

import requests

import config

JOBS_PAGE = "https://www.academictransfer.com/en/jobs/"
API = "https://api.academictransfer.com"
PHD_FUNCTION_TYPE = 9
PAGE_SIZE = 50


def _ua():
    return {"User-Agent": config.USER_AGENT, "Accept-Language": "en"}


def _get_public_token(session: requests.Session) -> str | None:
    """Extract $satDataApiPublicAccessToken from the jobs page Nuxt payload."""
    r = session.get(JOBS_PAGE, timeout=config.REQUEST_TIMEOUT)
    m = re.search(r'id="__NUXT_DATA__"[^>]*>(.*?)</script>', r.text, re.S)
    if not m:
        return None
    try:
        arr = json.loads(m.group(1))
    except json.JSONDecodeError:
        return None
    for el in arr:
        if isinstance(el, dict) and "$satDataApiPublicAccessToken" in el:
            idx = el["$satDataApiPublicAccessToken"]
            if isinstance(idx, int) and 0 <= idx < len(arr):
                val = arr[idx]
                if isinstance(val, str) and len(val) > 20:
                    return val
    # fallback: a long bare token string
    m2 = re.search(r'"([A-Za-z0-9]{30,50})"', m.group(1))
    return m2.group(1) if m2 else None


def _title(v: dict) -> str:
    trans = v.get("translations") or []
    for t in trans:
        if t.get("language_code") == "en" and t.get("title"):
            return t["title"]
    return trans[0]["title"] if trans and trans[0].get("title") else ""


def _date(s: str | None) -> str:
    if not s:
        return ""
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return s[:10]


def _is_life_science(title: str) -> bool:
    low = title.lower()
    return any(kw in low for kw in config.LIFE_SCIENCE_KEYWORDS)


def scrape(verbose: bool = True) -> list[dict]:
    s = requests.Session()
    s.headers.update(_ua())
    token = _get_public_token(s)
    if not token:
        if verbose:
            print("  AcademicTransfer: could not obtain public token; skipping")
        return []
    s.headers["Authorization"] = f"Bearer {token}"

    # Page through all PhD vacancies.
    vacancies, offset = [], 0
    while True:
        r = s.get(f"{API}/vacancies/", params={
            "function_types": PHD_FUNCTION_TYPE, "limit": PAGE_SIZE, "offset": offset,
        }, timeout=config.REQUEST_TIMEOUT)
        if r.status_code != 200:
            break
        d = r.json()
        batch = d.get("results", [])
        vacancies.extend(batch)
        if not d.get("next") or not batch:
            break
        offset += PAGE_SIZE
        time.sleep(config.REQUEST_DELAY_SECONDS)
    if verbose:
        print(f"  AcademicTransfer: {len(vacancies)} PhD vacancies")

    org_cache: dict[int, str] = {}
    def org_name(oid):
        if not oid:
            return ""
        if oid not in org_cache:
            try:
                rr = s.get(f"{API}/organisations/{oid}/", timeout=config.REQUEST_TIMEOUT)
                org_cache[oid] = rr.json().get("name", "") if rr.status_code == 200 else ""
            except (requests.RequestException, ValueError):
                org_cache[oid] = ""
        return org_cache[oid]

    records = []
    for v in vacancies:
        title = _title(v)
        if not _is_life_science(title):
            continue
        org = org_name(v.get("organisation"))
        records.append({
            "source": "AcademicTransfer (NL)",
            "id": f"at-{v.get('external_id')}",
            "title": title,
            "organisation": org,
            "host_institution": org,
            "country": "Netherlands",
            "number_of_offers": str(v.get("available_positions") or ""),
            "research_field": "Life sciences",
            "researcher_profile": "PhD",
            "funding_programme": "",
            "programme_type": "AcademicTransfer",
            "open_date": _date(v.get("created_datetime")),
            "deadline": _date(v.get("end_date")),
            "deadline_display": _date(v.get("end_date")),
            "start_date": "",
            "employment_type": "",
            "hours_per_week": str(v.get("max_weekly_hours") or ""),
            "education_level": "",
            "grant_agreement_number": "",
            "url": v.get("absolute_url") or v.get("short_url") or "",
            "detail_available": "yes",
        })
    if verbose:
        print(f"  AcademicTransfer: kept {len(records)} life-science PhD vacancies")
    return records


if __name__ == "__main__":
    for r in scrape():
        print(r["id"], "|", r["title"][:55], "|", r["deadline"], "|", r["organisation"][:30])
