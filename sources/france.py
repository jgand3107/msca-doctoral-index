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
DOCTORAT_API = "https://app.doctorat.gouv.fr/api/propositions-these"
DOCTORAT_LIFE_CODE = "5"   # domaineScientifique "Biologie, médecine et santé"
_UA = {"User-Agent": euraxess.config.USER_AGENT, "Accept": "text/html"}
_JSON_HDR = {"User-Agent": euraxess.config.USER_AGENT, "Accept": "application/json"}


def _d10(s):
    return (s or "")[:10]


def fetch_doctorat_all():
    """Fetch all offers from the French national doctoral portal (raw items)."""
    try:
        r = requests.get(DOCTORAT_API, params={
            "page": 0, "size": 1500, "sortField": "dateMiseEnLigne",
            "sortDirection": "DESC"}, headers=_JSON_HDR, timeout=euraxess.config.REQUEST_TIMEOUT)
        return r.json().get("content", []) if r.status_code == 200 else []
    except (requests.RequestException, ValueError):
        return []


def doctorat_record(it, city, source="doctorat.gouv.fr"):
    """Map a doctorat.gouv offer item to a common-schema record."""
    fin = it.get("financementTypes")
    fin = ", ".join(fin) if isinstance(fin, list) else (fin or "")
    url = (it.get("urlCandidature") or it.get("urlInfosComplementaires")
           or f"https://app.doctorat.gouv.fr/propositions/{it.get('id')}")
    return {
        "source": source, "id": "dg-" + str(it.get("id")),
        "title": (it.get("theseTitre") or it.get("theseTitreAnglais") or "").strip(),
        "organisation": it.get("etablissementLibelle") or "",
        "host_institution": it.get("uniteRechercheLibelle") or it.get("etablissementLibelle") or "",
        "country": "France", "city": city,
        "research_field": it.get("domaine") or "",
        "researcher_profile": "PhD", "funding_programme": fin,
        "programme_type": "doctorat.gouv.fr", "number_of_offers": "",
        "locations": (it.get("uniteRechercheVille") or it.get("etablissementVille") or ""),
        "open_date": _d10(it.get("dateMiseEnLigne")),
        "deadline": _d10(it.get("dateLimiteCandidature")),
        "deadline_display": _d10(it.get("dateLimiteCandidature")),
        "start_date": _d10(it.get("dateDebutThese")),
        "employment_type": "", "hours_per_week": "", "education_level": "",
        "grant_agreement_number": "", "url": url, "detail_available": "yes",
    }

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


def _doctorat_gouv(cities, verbose):
    """French national doctoral portal — biotech/life-science offers in `cities`."""
    items = fetch_doctorat_all()
    cu = [(c, c.upper()) for c in cities]
    out = []
    for it in items:
        city_raw = (it.get("uniteRechercheVille") or it.get("etablissementVille") or "").upper()
        match = next((c for c, u in cu if u in city_raw), None)
        if not match:
            continue
        if str(it.get("domaineScientifique")) != DOCTORAT_LIFE_CODE:
            continue
        out.append(france_doctorat_record(it, match))
    if verbose:
        print(f"  doctorat.gouv.fr: {len(out)} biotech/life-science PhD in {cities}")
    return out


def france_doctorat_record(it, city):
    rec = doctorat_record(it, city)
    rec["research_field"] = rec["research_field"] or "Biologie, médecine et santé"
    return rec


def scrape(verbose: bool = True) -> list[dict]:
    cities = config.FRANCE_CITIES
    records = _euraxess_france(cities, verbose)
    records += _doctorat_gouv(cities, verbose)
    try:
        records += _linkedin(cities, verbose)
    except Exception as exc:
        if verbose:
            print(f"  LinkedIn source error (skipped): {exc}")
    return records
