"""
France tracker — ALL biotech/life-science PhD vacancies in France.

Sources: EURAXESS France (R1, life-science) + doctorat.gouv.fr (the French
national doctoral portal, discipline "Biologie, médecine et santé").
`build()` takes pre-fetched data so run.py can scrape EURAXESS once and share.
"""
from __future__ import annotations

import requests

from sources import euraxess

DOCTORAT_API = "https://app.doctorat.gouv.fr/api/propositions-these"
DOCTORAT_LIFE_CODE = "5"   # domaineScientifique "Biologie, médecine et santé"
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


def build(eur_records, doctorat_items, verbose=True):
    """Everything-France: EURAXESS France (life-science) + doctorat.gouv (life-science)."""
    out = []
    for r in (eur_records or []):
        if euraxess.is_life_science(r.get("research_field", "")):
            r["source"] = "EURAXESS"
            out.append(r)
    n_eur = len(out)
    for it in (doctorat_items or []):
        if str(it.get("domaineScientifique")) != DOCTORAT_LIFE_CODE:
            continue
        city = (it.get("uniteRechercheVille") or it.get("etablissementVille") or "").title()
        rec = doctorat_record(it, city)
        rec["research_field"] = rec["research_field"] or "Biologie, médecine et santé"
        out.append(rec)
    if verbose:
        print(f"  France: {len(out)} life-science PhD "
              f"(EURAXESS {n_eur} + doctorat.gouv {len(out) - n_eur})")
    return out
