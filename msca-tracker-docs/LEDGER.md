# Project Ledger

**Project:** Weekly multi-source tracker of European doctoral (PhD) scholarships for life sciences, published as CSV/JSON + reports on GitHub.
**Started:** Tue, 20 Oct 2026 — ~10:00 (ledger backfilled at 16:17)
**Docs folder:** msca-tracker-docs/
**Repo:** https://github.com/jgand3107/msca-doctoral-index

---

## Session Log

### Tue, 20 Oct 2026 — Goal established
- Goal: an "API" that does a weekly thorough search of every MSCA **doctoral** (not postdoc) scholarship, as a table with key dates (opens, closes, start date).
- Decision: GitHub repo + weekly GitHub Actions cron writing CSV/JSON that R reads from the raw URL (chosen by user over a hosted server or local-only).

### Feasibility investigation (EURAXESS)
- **Action:** Probed the live EURAXESS jobs portal with the built-in browser + Python.
- **Result:** No public JSON API, but search is reachable via plain GET facet URLs:
  `?f[0]=job_research_profile:447&f[1]=job_is_eu_founded:4348&f[2]=job_is_eu_founded:4349`.
  - `job_research_profile:447` = First Stage Researcher (R1) → excludes postdocs.
  - `job_is_eu_founded:4348` = Horizon Europe – MSCA; `4349` = COFUND.
  - ~215 MSCA+COFUND R1 positions; 10/page; deadline in a `<time datetime>`; detail at `/jobs/<id>`.

### Build v1 — EURAXESS scraper (commit 76ca64d)
- Created `config.py`, `msca_scraper.py`, `run.py`, `requirements.txt`, `.gitignore`, `README.md`, `.github/workflows/weekly.yml`.
- Decision: stdlib `html.parser` (no lxml); start date is best-effort (EURAXESS rarely publishes it).

### Life-science filter (8438e9c)
- **Action:** Added keep-if-life-science research-field filter (`LIFE_SCIENCES_ONLY`, `LIFE_SCIENCE_KEYWORDS`).
- **Result:** 215 → 75 life-science positions; drops social sciences, humanities, pure eng/physics/CS.

### Reliability hardening (36bd1b8, 871383e, f38fbdd)
- **Error:** A GitHub Actions run scraped a degraded 2-row response (EURAXESS degrades cloud IPs) and committed it over good data; also a push race and a JSON line-merge that duplicated a record.
- **Resolution:**
  - `validate_scrape()` + `scrape_validated()` — reject results that don't match the R1/MSCA facets or are implausibly small; abort without overwriting good data; retry up to 8× with backoff, fresh session, browser UA + consent cookie.
  - `.gitattributes merge=ours` on data files (no line-merging).
  - Workflow commit step retries + merges on push rejection.

### Two runners (ae11132)
- **Decision:** EURAXESS degrades cloud IPs intermittently → added a **local** runner `run_and_push.ps1` + Windows Task Scheduler ("MSCA Doctoral Weekly Scrape", Mon 09:00, StartWhenAvailable) as the reliable path; GitHub Actions stays as free best-effort. Verified the local runner scrapes, validates, enriches, and pushes.

### Country filter (c14e284)
- **Action:** `COUNTRIES_FILTER` = Spain, France, United Kingdom, Germany, Italy, Netherlands, Switzerland.
- **Result:** 75 → 48 positions.

### Report + delivery
- Generated `msca_report.html` (styled, searchable/sortable); sent to user; published as a private Artifact: https://claude.ai/artifact/SkFqVNbr4FDREeiDBnkoBu

### Scope expansion (in progress)
- User requests: add **VHIO** + **la Caixa** to Tier-1; **AcademicTransfer** as a separate **Tier-2** report; an **annual deadlines calendar**.
- **Action:** Created `data/annual_deadlines.csv` (curated major recurring schemes; expected windows + official URLs).
- **Probe results:**
  - VHIO = Teamtailor board (`jobs.vhio.net`); detail JSON-LD has JobPosting (datePosted, location, type) but **no deadline** → parse from page body.
  - AcademicTransfer has a JSON API (`api.academictransfer.com`) → use that.
- **Also:** Ran project-init (this ledger) at user's request to keep steps + files ordered.

---

## Files Created
- `config.py` — scope/filters (profile, funding, life-science keywords, countries, retries).
- `msca_scraper.py` — EURAXESS source: faceted scrape, validation, detail enrichment.
- `run.py` — orchestration: scrape → filter → merge history → write CSV/JSON.
- `requirements.txt`, `.gitignore`, `.gitattributes`, `README.md`.
- `.github/workflows/weekly.yml` — weekly cloud runner.
- `run_and_push.ps1` — weekly local runner.
- `data/msca_doctoral_positions.csv` / `.json`, `data/last_run.json`.
- `data/annual_deadlines.csv` — curated recurring-scheme calendar.
- `msca_report.html` — generated report snapshot (gitignored).
- `msca-tracker-docs/LEDGER.md` — this ledger.

## Files Modified
- See Session Log; main edits were to `config.py`, `msca_scraper.py`, `run.py`, `weekly.yml`, `README.md`.

## Commands Run
- Scrapes via `python run.py` (local, validated); git init/commit/push; Windows `Register-ScheduledTask`.

## Decisions Made
- Delivery = GitHub repo + raw CSV URL (not a hosted server).
- Life-science + 7-country filters; R1-only (no postdocs).
- Never publish a degraded scrape (validation guard); two runners (cloud best-effort + local reliable).

## Errors Encountered
- Degraded cloud scrape overwrote good data → fixed with validation guard.
- JSON line-merge duplicated a record → fixed with `.gitattributes merge=ours`.
- Push race with concurrent Action → fixed with retry/merge in workflow.

### Tue, 20 Oct 2026 — 16:30 — VHIO source built
- **Action:** Added `vhio.py` (scrapes jobs.vhio.net Teamtailor board; JSON-LD + body deadline parse; flags predoc/PhD/fellowship listings).
- **Result:** Parses all 16 current listings with deadlines; 0 are scholarships right now (VHIO has only staff/technician roles posted) — will auto-capture predoc/PhD when posted.

## Outstanding / Next
- Wire `vhio.py` into run.py Tier-1 (add a `source` column to the schema).
- Build AcademicTransfer (Tier-2, via api.academictransfer.com).
- Represent la Caixa via the deadlines calendar + any live INPhINIT positions.
- Produce Tier-1 + Tier-2 reports and refresh the hosted report.
