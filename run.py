"""
Entry point: build the geographic doctoral-scholarship tabs.

Tab 1 MSCA       -> data/msca_doctoral_positions.*  (MSCA/COFUND, FR/ES/IT/UK)
Tab 2 France     -> data/france_phd.*               (all life-science PhD in FR)
Tab 3 Spain      -> data/spain_phd.*                 (all life-science PhD in ES)
Tab 4 Industry   -> data/industry_phd.*             (industry PhD in FR & ES)
Cancer radar     -> data/cancer_centres_radar.*     (top cancer institutes)
Plus data/annual_deadlines_status.json (recurring schemes, estimated status).

Each EURAXESS facet set is scraped at most once per run and shared across tabs.

Usage:
    python run.py                 # full build
    python run.py --no-details    # skip EURAXESS detail enrichment (faster)
    python run.py --msca-only / --france-only / --spain-only / --industry-only / --radar-only

The weekly runners (GitHub Actions / run_and_push.ps1) just call `python run.py`.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys

import config
from sources import euraxess, vhio, deadlines, france, spain, cancer_radar

# Column order for the CSVs (source first).
COLUMNS = [
    "source", "id", "title", "programme_type", "funding_programme",
    "researcher_profile", "organisation", "host_institution", "centre",
    "country", "city", "research_field", "number_of_offers", "open_date", "deadline",
    "deadline_display", "start_date", "employment_type", "hours_per_week",
    "education_level", "grant_agreement_number", "url", "detail_available",
    "first_seen", "last_seen",
]

CARRY_FORWARD = [
    "start_date", "employment_type", "hours_per_week",
    "education_level", "grant_agreement_number",
]


def load_history(json_path: str) -> dict[str, dict]:
    if not os.path.exists(json_path):
        return {}
    try:
        with open(json_path, "r", encoding="utf-8") as fh:
            prev = json.load(fh)
        return {r["id"]: r for r in prev.get("positions", prev) if "id" in r}
    except (json.JSONDecodeError, KeyError, TypeError):
        return {}


def finalize_and_write(records, csv_path, json_path, run_ts, label, meta_extra=None):
    """Merge history (first_seen + carry-forward), sort, write CSV + JSON."""
    today = run_ts[:10]
    history = load_history(json_path)
    for r in records:
        prev = history.get(r["id"])
        r["first_seen"] = prev["first_seen"] if prev and prev.get("first_seen") else today
        r["last_seen"] = today
        if prev:
            for field in CARRY_FORWARD:
                if not r.get(field) and prev.get(field):
                    r[field] = prev[field]

    records.sort(key=lambda r: (r["deadline"] == "", r["deadline"]))

    payload = {
        "generated_at": run_ts,
        "tier": label,
        "count": len(records),
        "positions": records,
    }
    if meta_extra:
        payload.update(meta_extra)
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
    with open(csv_path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS, extrasaction="ignore")
        w.writeheader()
        for r in records:
            w.writerow(r)
    print(f"  wrote {len(records)} rows -> {csv_path}")


# --- Shared EURAXESS scrapes (each facet set scraped at most once per run) ---
_EUR_CACHE: dict = {}
_SHARED: dict = {}


def eur(facets, require_funding=False):
    """Cached EURAXESS scrape. Returns records, or None if degraded."""
    key = (tuple(facets), require_funding)
    if key not in _EUR_CACHE:
        try:
            recs, _ = euraxess.scrape_validated(
                facets=list(facets), require_funding=require_funding, verbose=False)
            _EUR_CACHE[key] = recs
        except euraxess.ScrapeValidationError as exc:
            print(f"  EURAXESS scrape degraded ({exc})", file=sys.stderr)
            _EUR_CACHE[key] = None
    return _EUR_CACHE[key]


def _profile_country(code):
    return [f"job_research_profile:{config.RESEARCHER_PROFILE}", f"job_country:{code}"]


def doctorat_items():
    if "doctorat" not in _SHARED:
        _SHARED["doctorat"] = france.fetch_doctorat_all()
    return _SHARED["doctorat"]


def vhio_records():
    if "vhio" not in _SHARED:
        try:
            _SHARED["vhio"] = vhio.scrape(scholarships_only=True, verbose=False)
        except Exception as exc:
            print(f"  VHIO error (skipped): {exc}", file=sys.stderr)
            _SHARED["vhio"] = []
    return _SHARED["vhio"]


def build_msca(args, run_ts) -> bool:
    """Tab 1: EURAXESS MSCA/COFUND, life-science, MSCA_COUNTRIES."""
    print("== Tab 1: MSCA/COFUND (FR/ES/IT/UK) ==")
    base = eur(euraxess.default_facets(), require_funding=True)
    if base is None:
        print("  ABORTING Tab 1: degraded; data untouched.", file=sys.stderr)
        return False
    records = [dict(r) for r in base]
    if config.LIFE_SCIENCES_ONLY:
        records = [r for r in records if euraxess.is_life_science(r["research_field"])]
    allow = {c.lower() for c in config.MSCA_COUNTRIES}
    records = [r for r in records if (r["country"] or "").lower() in allow]
    print(f"  MSCA: {len(records)} life-science in {config.MSCA_COUNTRIES}")
    if args.limit:
        records = records[:args.limit]
    if config.ENRICH_DETAILS and not args.no_details:
        print("  enriching detail pages (best-effort)...")
        euraxess.enrich_all(records)
    else:
        for r in records:
            r["detail_available"] = r.get("detail_available") or "skipped"
    finalize_and_write(records, os.path.join(args.output_dir, config.CSV_FILE),
                       os.path.join(args.output_dir, config.JSON_FILE), run_ts, "tab1-msca")
    return True


def build_france(args, run_ts) -> bool:
    if not getattr(config, "FRANCE_ENABLED", False):
        return True
    print("== Tab 2: everything France (life-science) ==")
    fr = eur(_profile_country(config.FRANCE_COUNTRY_CODE))
    if fr is None:
        print("  ABORTING Tab 2: EURAXESS France degraded; data untouched.", file=sys.stderr)
        return False
    records = france.build([dict(r) for r in fr], doctorat_items())
    finalize_and_write(records, os.path.join(args.output_dir, config.FRANCE_CSV_FILE),
                       os.path.join(args.output_dir, config.FRANCE_JSON_FILE), run_ts, "france-all")
    return True


def build_spain(args, run_ts) -> bool:
    if not getattr(config, "SPAIN_ENABLED", False):
        return True
    print("== Tab 3: everything Spain (life-science) ==")
    sp = eur(_profile_country(config.SPAIN_COUNTRY_CODE))
    if sp is None:
        print("  ABORTING Tab 3: EURAXESS Spain degraded; data untouched.", file=sys.stderr)
        return False
    records = spain.build([dict(r) for r in sp], vhio_records())
    finalize_and_write(records, os.path.join(args.output_dir, config.SPAIN_CSV_FILE),
                       os.path.join(args.output_dir, config.SPAIN_JSON_FILE), run_ts, "spain-all")
    return True


def build_industry(args, run_ts) -> bool:
    print("== Tab 4: Industry PhD (FR/ES) ==")
    facets = [f"job_research_profile:{config.RESEARCHER_PROFILE}"]
    facets += [f"job_organisation_type:{o}" for o in config.INDUSTRY_ORG_TYPES]
    base = eur(facets)
    if base is None:
        print("  ABORTING Tab 4: degraded; data untouched.", file=sys.stderr)
        return False
    records = []
    for r in base:
        r2 = dict(r)
        r2["source"] = "Industry (EURAXESS)"
        r2["programme_type"] = "Industry"
        records.append(r2)
    if config.LIFE_SCIENCES_ONLY:
        records = [r for r in records if euraxess.is_life_science(r["research_field"])]
    allow = {c.lower() for c in config.INDUSTRY_COUNTRIES}
    records = [r for r in records if (r["country"] or "").lower() in allow]
    print(f"  Industry: {len(records)} life-science in {config.INDUSTRY_COUNTRIES}")
    finalize_and_write(records, os.path.join(args.output_dir, config.TIER3_CSV_FILE),
                       os.path.join(args.output_dir, config.TIER3_JSON_FILE), run_ts, "tab4-industry")
    return True


def build_radar(args, run_ts) -> bool:
    if not getattr(config, "RADAR_ENABLED", False):
        return True
    print("== Cancer-centres radar (doctorat.gouv.fr + EURAXESS Spain + VHIO) ==")
    sp = eur(_profile_country(config.SPAIN_COUNTRY_CODE))  # reuses Tab 3's scrape
    records = cancer_radar.build(doctorat_items(), sp or [], vhio_records())
    finalize_and_write(records, os.path.join(args.output_dir, config.RADAR_CSV_FILE),
                       os.path.join(args.output_dir, config.RADAR_JSON_FILE), run_ts, "cancer-radar")
    return True


def main() -> None:
    ap = argparse.ArgumentParser(description="Build the geographic doctoral-scholarship tabs.")
    ap.add_argument("--no-details", action="store_true", help="skip EURAXESS detail enrichment")
    ap.add_argument("--limit", type=int, default=0, help="cap MSCA listings (debug)")
    ap.add_argument("--msca-only", action="store_true")
    ap.add_argument("--france-only", action="store_true")
    ap.add_argument("--spain-only", action="store_true")
    ap.add_argument("--industry-only", action="store_true")
    ap.add_argument("--radar-only", action="store_true")
    ap.add_argument("--output-dir", default=config.OUTPUT_DIR)
    args = ap.parse_args()
    os.makedirs(args.output_dir, exist_ok=True)

    only = (args.msca_only or args.france_only or args.spain_only
            or args.industry_only or args.radar_only)
    run_ts = euraxess.now_iso()
    print(f"[{run_ts}] geographic scholarship build starting")

    ok1 = okfr = oksp = okind = okr = True
    if args.msca_only or not only:
        ok1 = build_msca(args, run_ts)
    if args.france_only or not only:
        okfr = build_france(args, run_ts)
    if args.spain_only or not only:
        oksp = build_spain(args, run_ts)
    if args.industry_only or not only:
        okind = build_industry(args, run_ts)
    if args.radar_only or not only:
        okr = build_radar(args, run_ts)

    # Recurring-scheme calendar with an estimated open/upcoming status for today.
    dl = deadlines.load(verbose=True)
    with open(os.path.join(args.output_dir, "annual_deadlines_status.json"),
              "w", encoding="utf-8") as fh:
        json.dump({"generated_at": run_ts, "note": "status is estimated from "
                   "expected windows, not a live confirmation", "schemes": dl},
                  fh, indent=2, ensure_ascii=False)

    with open(os.path.join(args.output_dir, config.META_FILE), "w", encoding="utf-8") as fh:
        json.dump({"generated_at": run_ts, "msca_ok": ok1, "france_ok": okfr,
                   "spain_ok": oksp, "industry_ok": okind, "radar_ok": okr,
                   "deadlines_open_now": sum(1 for r in dl if r["status"] == "open")},
                  fh, indent=2)

    # Each tab only writes valid data (a degraded tab leaves its files
    # untouched), so the runners can commit whatever changed. Exit non-zero
    # only when the primary tab failed, as an alert signal.
    primary_ok = (okfr if args.france_only else oksp if args.spain_only
                  else okind if args.industry_only else okr if args.radar_only else ok1)
    if not primary_ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
