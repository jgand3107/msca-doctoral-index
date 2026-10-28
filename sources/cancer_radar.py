"""
Cancer-centres radar — track *every* PhD coming out of a curated list of top
cancer research institutes in Spain & France.

Sources (chosen for comprehensiveness without hammering one site too hard):
  * doctorat.gouv.fr — the French national doctoral portal (one JSON call);
    matches the French institutes. All disciplines (a PhD at a cancer centre
    counts, whatever the field).
  * EURAXESS Spain (R1) — matches the Spanish institutes.
  * VHIO (Teamtailor) — Barcelona, #2 on the list, its own board.

Matching is by institute name/alias (accent-insensitive) against each offer's
organisation / lab / city / title. Add or edit institutes in CENTRES.
"""
from __future__ import annotations

import collections
import re
import unicodedata

from sources import euraxess, vhio, france

# Each centre: canonical name, country, city, and aliases to match on.
# Short aliases (<=5 chars) are matched on word boundaries to avoid false hits.
CENTRES = [
    # --- France ---
    {"name": "Gustave Roussy", "country": "France", "city": "Villejuif (Paris)",
     "aliases": ["gustave roussy", "igr"]},
    {"name": "Institut Curie", "country": "France", "city": "Paris",
     "aliases": ["institut curie"]},
    {"name": "Centre Léon Bérard / CRCL", "country": "France", "city": "Lyon",
     "aliases": ["leon berard", "crcl", "cancer research cent", "cancerologie de lyon"]},
    {"name": "Centre de Recherche des Cordeliers", "country": "France", "city": "Paris",
     "aliases": ["cordeliers"]},
    {"name": "Institut Paoli-Calmettes / CRCM", "country": "France", "city": "Marseille",
     "aliases": ["paoli-calmettes", "paoli calmettes", "crcm", "cancerologie de marseille"]},
    {"name": "Centre d'Immunologie de Marseille-Luminy (CIML)", "country": "France", "city": "Marseille",
     "aliases": ["immunologie de marseille", "marseille-luminy", "ciml"]},
    {"name": "IUCT-Oncopole / CRCT", "country": "France", "city": "Toulouse",
     "aliases": ["oncopole", "crct", "cancerologie de toulouse", "iuct"]},
    {"name": "Institut Cochin", "country": "France", "city": "Paris",
     "aliases": ["institut cochin"]},
    {"name": "IGBMC", "country": "France", "city": "Strasbourg",
     "aliases": ["igbmc", "genetique et de biologie moleculaire"]},
    {"name": "Institut Bergonié", "country": "France", "city": "Bordeaux",
     "aliases": ["bergonie"]},
    {"name": "Institut Pasteur", "country": "France", "city": "Paris",
     "aliases": ["institut pasteur"]},
    {"name": "Institut Imagine / Necker", "country": "France", "city": "Paris",
     "aliases": ["institut imagine", "imagine", "necker"]},
    {"name": "Institut de Génétique Humaine (IGH)", "country": "France", "city": "Montpellier",
     "aliases": ["genetique humaine", "igh"]},
    # --- Spain ---
    {"name": "Vall d'Hebron Institute of Oncology (VHIO)", "country": "Spain", "city": "Barcelona",
     "aliases": ["vhio", "vall d'hebron institute of oncology", "vall d hebron institute", "vall d'hebron"]},
    {"name": "IRB Barcelona", "country": "Spain", "city": "Barcelona",
     "aliases": ["irb barcelona", "institute for research in biomedicine", "institut de recerca biomedica"]},
    {"name": "CNIO", "country": "Spain", "city": "Madrid",
     "aliases": ["cnio", "centro nacional de investigaciones oncologicas", "spanish national cancer"]},
    {"name": "IDIBAPS / Hospital Clínic", "country": "Spain", "city": "Barcelona",
     "aliases": ["idibaps", "hospital clinic"]},
    {"name": "Josep Carreras Leukaemia Research Institute", "country": "Spain", "city": "Barcelona",
     "aliases": ["josep carreras", "carreras leukaemia", "carreras leukemia"]},
    {"name": "Catalan Institute of Oncology / IDIBELL", "country": "Spain", "city": "Barcelona",
     "aliases": ["idibell", "catalan institute of oncology", "institut catala d'oncologia"]},
    {"name": "CIC-IBMCC", "country": "Spain", "city": "Salamanca",
     "aliases": ["cic-ibmcc", "ibmcc", "investigacion del cancer", "cancer research center salamanca"]},
    {"name": "Hospital 12 de Octubre / imas12", "country": "Spain", "city": "Madrid",
     "aliases": ["12 de octubre", "imas12", "doce de octubre"]},
    {"name": "IMIM / Hospital del Mar", "country": "Spain", "city": "Barcelona",
     "aliases": ["hospital del mar", "imim"]},
    {"name": "INCLIVA", "country": "Spain", "city": "Valencia",
     "aliases": ["incliva"]},
    {"name": "IBiS (Institute of Biomedicine of Seville)", "country": "Spain", "city": "Seville",
     "aliases": ["biomedicine of seville", "biomedicina de sevilla", "ibis"]},
    {"name": "CABIMER", "country": "Spain", "city": "Seville",
     "aliases": ["cabimer"]},
]


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", s)


def match_centre(text: str, country: str | None = None):
    t = _norm(text)
    for c in CENTRES:
        if country and c["country"] != country:
            continue
        for a in c["aliases"]:
            an = _norm(a)
            hit = (re.search(r"\b" + re.escape(an) + r"\b", t) if len(an) <= 5 else an in t)
            if hit:
                return c
    return None


def _from_doctorat():
    out = []
    for it in france.fetch_doctorat_all():
        blob = " ".join(str(it.get(k) or "") for k in (
            "uniteRechercheLibelle", "etablissementLibelle",
            "uniteRechercheVille", "etablissementVille", "theseTitre"))
        c = match_centre(blob, country="France")
        if not c:
            continue
        rec = france.doctorat_record(it, c["city"])
        rec["centre"] = c["name"]
        out.append(rec)
    return out


def _from_euraxess_spain():
    try:
        recs, _ = euraxess.scrape_validated(
            facets=["job_research_profile:447", "job_country:788"],
            require_funding=False, verbose=False)
    except euraxess.ScrapeValidationError:
        return []
    out = []
    for r in recs:
        blob = " ".join(str(r.get(k) or "") for k in
                        ("organisation", "host_institution", "locations", "title"))
        c = match_centre(blob, country="Spain")
        if not c:
            continue
        r["source"] = "EURAXESS"
        r["centre"] = c["name"]
        r["city"] = c["city"]
        out.append(r)
    return out


def _from_vhio():
    recs = vhio.scrape(scholarships_only=True, verbose=False)
    for r in recs:
        r["centre"] = "Vall d'Hebron Institute of Oncology (VHIO)"
        r["city"] = "Barcelona"
    return recs


def scrape(verbose: bool = True) -> list[dict]:
    out = _from_doctorat() + _from_euraxess_spain() + _from_vhio()
    seen = {}
    for r in out:
        seen.setdefault(r.get("url") or r.get("id"), r)
    recs = list(seen.values())
    for r in recs:  # show the centre as the org, keep the raw lab in host_institution
        if r.get("centre"):
            r["organisation"] = r["centre"]
    if verbose:
        by = collections.Counter(r.get("centre") for r in recs)
        print(f"  cancer radar: {len(recs)} PhD across {len(by)} centres")
        for name, n in by.most_common():
            print(f"      {n:2}  {name}")
    return recs
