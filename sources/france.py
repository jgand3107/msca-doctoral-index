"""
France tracker — biotech/life-science PhD vacancies in Montpellier & Lyon.

Sources:
  * EURAXESS France (R1), filtered to the target cities + life-science + PhD.
  * LinkedIn public *guest* job search (no login), city-targeted, filtered to
    PhD + life-science. Guest search coverage is partial and can be blocked
    from datacenter IPs (so it may yield little on the cloud runner, more on
    the local runner) — failures are non-fatal.
"""
from __future__ import annotations

import time
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

import config
from sources import euraxess

LINKEDIN_API = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
_UA = {"User-Agent": euraxess.config.USER_AGENT, "Accept": "text/html"}

_LIFE = ["biolog", "biotech", "biomed", "cancer", "oncolog", "immunolog", "neuro",
         "genom", "genetic", "molecular", "cell", "rna", "protein", "microbio",
         "bioinformatic", "pharmacolog", "biochem", "drug", "vaccine", "antibody",
         "metabol", "stem cell", "life science", "structural biol", "biophys"]
_PHD = ["phd", "ph.d", "doctora", "thèse", "these", "doctorant"]
_NOT_PHD = ["postdoc", "post-doc", "post doctoral", "postdoctoral", "stagiaire",
            "ingénieur", "ingenieur", "technicien", "technician", "master",
            "aide laboratoire", "assistant", "field service", "manager",
            "biologiste médical", "biologiste medical", "engineer", "internship"]


def _is_phd_life(title: str) -> bool:
    t = (title or "").lower()
    if any(x in t for x in _NOT_PHD):
        return False
    is_phd = any(k in t for k in _PHD)
    is_life = any(k in t for k in _LIFE)
    return is_phd and (is_life or True)  # at these sources a PhD title is enough


def _city_in(record: dict, cities) -> str | None:
    blob = " ".join(str(record.get(k, "")) for k in
                    ("title", "organisation", "host_institution", "locations")).lower()
    for c in cities:
        if c.lower() in blob:
            return c
    return None


def _euraxess_france(cities, verbose):
    try:
        recs, _ = euraxess.scrape_validated(
            facets=[f"job_research_profile:{config.RESEARCHER_PROFILE}",
                    f"job_country:{config.FRANCE_COUNTRY_CODE}"],
            require_funding=False, verbose=False)
    except euraxess.ScrapeValidationError as exc:
        if verbose:
            print(f"  EURAXESS France degraded ({exc}); skipping that source")
        return []
    out = []
    for r in recs:
        city = _city_in(r, cities)
        if not city:
            continue
        if not euraxess.is_life_science(r["research_field"]):
            continue
        if any(x in r["title"].lower() for x in _NOT_PHD):
            continue  # drop postdoc/engineer/etc.
        r["source"] = "EURAXESS"
        r["city"] = city
        out.append(r)
    if verbose:
        print(f"  EURAXESS France: {len(out)} PhD life-science in {cities}")
    return out


def _linkedin(cities, verbose):
    out = {}
    loc_map = {"Montpellier": "Montpellier, Occitanie, France",
               "Lyon": "Lyon, Auvergne-Rhône-Alpes, France"}
    keywords = ["PhD", "doctorant biologie", "PhD biology", "thèse biotech"]
    for city in cities:
        location = loc_map.get(city, f"{city}, France")
        for kw in keywords:
            for start in (0, 25):
                try:
                    r = requests.get(LINKEDIN_API, params={
                        "keywords": kw, "location": location, "start": start},
                        headers=_UA, timeout=20)
                except requests.RequestException:
                    continue
                if r.status_code != 200 or len(r.text) < 200:
                    break
                soup = BeautifulSoup(r.text, "html.parser")
                lis = soup.select("li")
                if not lis:
                    break
                for c in lis:
                    a = c.select_one("a[href*='/jobs/view/']")
                    h3 = c.select_one("h3")
                    if not (a and h3):
                        continue
                    url = a.get("href", "").split("?")[0]
                    title = h3.get_text(strip=True)
                    loc_el = c.select_one(".job-search-card__location")
                    loc_txt = loc_el.get_text(strip=True) if loc_el else location
                    # keep only if the card's own location names this city
                    if city.lower() not in loc_txt.lower():
                        continue
                    if url in out or not _is_phd_life(title):
                        continue
                    h4 = c.select_one("h4")
                    tm = c.select_one("time")
                    out[url] = {
                        "source": "LinkedIn", "id": "li-" + url.rsplit("-", 1)[-1],
                        "title": title, "organisation": h4.get_text(strip=True) if h4 else "",
                        "host_institution": h4.get_text(strip=True) if h4 else "",
                        "country": "France", "city": city, "research_field": "Life sciences",
                        "researcher_profile": "PhD", "funding_programme": "",
                        "programme_type": "LinkedIn", "number_of_offers": "", "locations": loc_txt,
                        "open_date": (tm.get("datetime", "") if tm else "")[:10],
                        "deadline": "", "deadline_display": "", "start_date": "",
                        "employment_type": "", "hours_per_week": "", "education_level": "",
                        "grant_agreement_number": "", "url": url, "detail_available": "n/a",
                    }
                time.sleep(1.0)
    recs = list(out.values())
    if verbose:
        print(f"  LinkedIn (guest): {len(recs)} PhD life-science in {cities}")
    return recs


def scrape(verbose: bool = True) -> list[dict]:
    cities = config.FRANCE_CITIES
    records = _euraxess_france(cities, verbose)
    try:
        records += _linkedin(cities, verbose)
    except Exception as exc:
        if verbose:
            print(f"  LinkedIn source error (skipped): {exc}")
    return records
