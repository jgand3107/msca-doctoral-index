"""
Entry point: build the multi-source doctoral-scholarship tables.

Tier 1 (main report)  -> data/msca_doctoral_positions.csv / .json
    EURAXESS MSCA+COFUND (R1, life-science, selected countries)
    + VHIO predoctoral/PhD listings
    + la Caixa INPhINIT tracked calls
Tier 2 (Netherlands)  -> data/netherlands_phd.csv / .json
    AcademicTransfer life-science PhD vacancies
Plus the curated data/annual_deadlines.csv (recurring schemes).

Usage:
    python run.py                 # full build (both tiers)
    python run.py --no-details    # skip EURAXESS detail enrichment (faster)
    python run.py --tier1-only / --tier2-only

The weekly runners (GitHub Actions / run_and_push.ps1) just call `python run.py`.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys

import config
from sources import euraxess, vhio, academictransfer, lacaixa

# Column order for the CSVs (source first).
COLUMNS = [
    "source", "id", "title", "programme_type", "funding_programme",
    "researcher_profile", "organisation", "host_institution", "country",
    "research_field", "number_of_offers", "open_date", "deadline",
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


def build_tier1(args, run_ts) -> bool:
    """EURAXESS + VHIO + la Caixa. Returns False if it aborted (no write)."""
    print("== Tier 1: EURAXESS (MSCA/COFUND) + VHIO + la Caixa ==")
    session = euraxess._session()
    try:
        records, expected_total = euraxess.scrape_validated(session)
    except euraxess.ScrapeValidationError as exc:
        print(f"  ABORTING Tier 1: EURAXESS scrape failed validation ({exc}).",
              file=sys.stderr)
        print("  Tier-1 data left untouched (not overwriting good data).",
              file=sys.stderr)
        return False

    if config.LIFE_SCIENCES_ONLY:
        before = len(records)
        records = [r for r in records if euraxess.is_life_science(r["research_field"])]
        print(f"  life-science filter: kept {len(records)}/{before}")
    if config.COUNTRIES_FILTER:
        before = len(records)
        allow = {c.lower() for c in config.COUNTRIES_FILTER}
        records = [r for r in records if (r["country"] or "").lower() in allow]
        print(f"  country filter: kept {len(records)}/{before}")
    if args.limit:
        records = records[:args.limit]

    if config.ENRICH_DETAILS and not args.no_details:
        print("  enriching EURAXESS detail pages (best-effort)...")
        euraxess.enrich_all(records, session)
    else:
        for r in records:
            r["detail_available"] = r.get("detail_available") or "skipped"

    # Additional Tier-1 sources.
    try:
        records += vhio.scrape(scholarships_only=True)
    except Exception as exc:  # a source failure must not sink the whole tier
        print(f"  VHIO source error (skipped): {exc}", file=sys.stderr)
    records += lacaixa.scrape()

    csv_path = os.path.join(args.output_dir, config.CSV_FILE)
    json_path = os.path.join(args.output_dir, config.JSON_FILE)
    finalize_and_write(records, csv_path, json_path, run_ts, "tier1-main")
    return True


def build_tier2(args, run_ts) -> bool:
    print("== Tier 2: AcademicTransfer (Netherlands, life-science PhD) ==")
    try:
        records = academictransfer.scrape()
    except Exception as exc:
        print(f"  AcademicTransfer error (Tier-2 left untouched): {exc}", file=sys.stderr)
        return False
    if not records:
        print("  no Tier-2 records returned; leaving existing data untouched")
        return False
    csv_path = os.path.join(args.output_dir, config.TIER2_CSV_FILE)
    json_path = os.path.join(args.output_dir, config.TIER2_JSON_FILE)
    finalize_and_write(records, csv_path, json_path, run_ts, "tier2-netherlands")
    return True


def main() -> None:
    ap = argparse.ArgumentParser(description="Build multi-source doctoral scholarship tables.")
    ap.add_argument("--no-details", action="store_true", help="skip EURAXESS detail enrichment")
    ap.add_argument("--limit", type=int, default=0, help="cap EURAXESS listings (debug)")
    ap.add_argument("--tier1-only", action="store_true")
    ap.add_argument("--tier2-only", action="store_true")
    ap.add_argument("--output-dir", default=config.OUTPUT_DIR)
    args = ap.parse_args()
    os.makedirs(args.output_dir, exist_ok=True)

    run_ts = euraxess.now_iso()
    print(f"[{run_ts}] multi-source scholarship build starting")

    ok1 = ok2 = True
    if not args.tier2_only:
        ok1 = build_tier1(args, run_ts)
    if not args.tier1_only:
        ok2 = build_tier2(args, run_ts)

    with open(os.path.join(args.output_dir, config.META_FILE), "w", encoding="utf-8") as fh:
        json.dump({"generated_at": run_ts, "tier1_ok": ok1, "tier2_ok": ok2}, fh, indent=2)

    # Each tier only writes valid data (a degraded tier leaves its files
    # untouched), so the runners can safely commit whatever changed. We exit
    # non-zero only when the PRIMARY tier failed, purely as an alert signal —
    # the runners commit valid data first, then propagate this.
    primary_ok = ok2 if args.tier2_only else ok1
    if not primary_ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
