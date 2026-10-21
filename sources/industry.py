"""
Source: EURAXESS industry PhD positions — TIER 3.

Reuses the EURAXESS scraper but with an organisation-type facet (Large
Enterprise + SME/Start-up) instead of the MSCA funding facet, so it captures
R1/PhD positions hosted by companies (including MSCA Industrial Doctorates and
company-funded PhDs). Filtered to life-science fields in the shortlisted
countries, same as Tier 1.
"""
from __future__ import annotations

import config
from sources import euraxess


def scrape(verbose: bool = True) -> list[dict]:
    facets = [f"job_research_profile:{config.RESEARCHER_PROFILE}"]
    for ot in config.INDUSTRY_ORG_TYPES:
        facets.append(f"job_organisation_type:{ot}")

    # No funding facet here, so don't require a funding programme in validation.
    records, _ = euraxess.scrape_validated(
        facets=facets, require_funding=False, verbose=verbose)

    for r in records:
        r["source"] = "Industry (EURAXESS)"
        r["programme_type"] = "Industry"

    if config.LIFE_SCIENCES_ONLY:
        before = len(records)
        records = [r for r in records if euraxess.is_life_science(r["research_field"])]
        if verbose:
            print(f"  Industry life-science filter: kept {len(records)}/{before}")
    if config.COUNTRIES_FILTER:
        allow = {c.lower() for c in config.COUNTRIES_FILTER}
        records = [r for r in records if (r["country"] or "").lower() in allow]
        if verbose:
            print(f"  Industry country filter: kept {len(records)}")
    return records
