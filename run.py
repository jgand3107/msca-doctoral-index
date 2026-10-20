"""
Entry point: scrape MSCA doctoral (R1) positions from EURAXESS and write
a CSV + JSON table that you can read straight into R or Python.

Usage:
    python run.py                 # full scrape + detail enrichment
    python run.py --no-details    # listings only (faster)
    python run.py --limit 20      # debug: only first N listings enriched

The weekly GitHub Actions workflow just runs `python run.py`.
"""

from __future__ import annotations

import argparse
import csv
import json
import os

import config
import msca_scraper as scraper

# Column order for the CSV (and the key order people will see).
COLUMNS = [
    "id",
    "title",
    "programme_type",
    "funding_programme",
    "researcher_profile",
    "organisation",
    "host_institution",
    "country",
    "research_field",
    "number_of_offers",
    "open_date",
    "deadline",
    "deadline_display",
    "start_date",
    "employment_type",
    "hours_per_week",
    "education_level",
    "grant_agreement_number",
    "url",
    "detail_available",
    "first_seen",
    "last_seen",
]


def load_history(json_path: str) -> dict[str, dict]:
    """Return {id: previous_record} so first_seen survives across runs."""
    if not os.path.exists(json_path):
        return {}
    try:
        with open(json_path, "r", encoding="utf-8") as fh:
            prev = json.load(fh)
        return {r["id"]: r for r in prev.get("positions", prev) if "id" in r}
    except (json.JSONDecodeError, KeyError, TypeError):
        return {}


def main() -> None:
    ap = argparse.ArgumentParser(description="Scrape MSCA doctoral positions from EURAXESS.")
    ap.add_argument("--no-details", action="store_true",
                    help="skip per-listing detail enrichment (no start dates)")
    ap.add_argument("--limit", type=int, default=0,
                    help="only keep the first N listings (debugging)")
    ap.add_argument("--output-dir", default=config.OUTPUT_DIR)
    args = ap.parse_args()

    out_dir = args.output_dir
    os.makedirs(out_dir, exist_ok=True)
    csv_path = os.path.join(out_dir, config.CSV_FILE)
    json_path = os.path.join(out_dir, config.JSON_FILE)
    meta_path = os.path.join(out_dir, config.META_FILE)

    run_ts = scraper.now_iso()
    today = run_ts[:10]
    print(f"[{run_ts}] MSCA doctoral scrape starting")
    print(f"  profile=R1({config.RESEARCHER_PROFILE}) "
          f"funding={list(config.FUNDING_PROGRAMMES.values())}")

    session = scraper._session()
    records = scraper.scrape_listings(session)

    if config.LIFE_SCIENCES_ONLY:
        before = len(records)
        records = [r for r in records if scraper.is_life_science(r["research_field"])]
        print(f"  life-science filter: kept {len(records)}/{before} "
              f"(dropped {before - len(records)} non-life-science)")

    if args.limit:
        records = records[:args.limit]

    if config.ENRICH_DETAILS and not args.no_details:
        print("Enriching detail pages (best-effort)...")
        scraper.enrich_all(records, session)
    else:
        for r in records:
            r["detail_available"] = "skipped"

    # Merge with history: preserve first_seen, and carry forward enrichment
    # fields we captured on a previous run (detail pages serve intermittently,
    # so this keeps the dataset monotonically richer instead of flickering).
    carry_forward = [
        "start_date", "employment_type", "hours_per_week",
        "education_level", "grant_agreement_number",
    ]
    history = load_history(json_path)
    for r in records:
        prev = history.get(r["id"])
        r["first_seen"] = prev["first_seen"] if prev and prev.get("first_seen") else today
        r["last_seen"] = today
        if prev:
            for field in carry_forward:
                if not r.get(field) and prev.get(field):
                    r[field] = prev[field]

    # Sort by soonest deadline (blank deadlines last).
    records.sort(key=lambda r: (r["deadline"] == "", r["deadline"]))

    # --- write JSON ---
    payload = {
        "generated_at": run_ts,
        "source": "EURAXESS jobs portal",
        "filters": {
            "researcher_profile": config.RESEARCHER_PROFILE,
            "funding_programmes": config.FUNDING_PROGRAMMES,
        },
        "count": len(records),
        "positions": records,
    }
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)

    # --- write CSV ---
    with open(csv_path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for r in records:
            writer.writerow(r)

    # --- write run metadata ---
    with open(meta_path, "w", encoding="utf-8") as fh:
        json.dump({
            "generated_at": run_ts,
            "count": len(records),
            "with_start_date": sum(1 for r in records if r.get("start_date")),
        }, fh, indent=2)

    print(f"Wrote {len(records)} positions:")
    print(f"  {csv_path}")
    print(f"  {json_path}")


if __name__ == "__main__":
    main()
