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
- Added `vhio.py` (Teamtailor board). Title-only scholarship match (body "PhD"
  in requirements caused false positives on staff jobs — fixed).

### Tue, 20 Oct 2026 — ~17:00 — Multi-source tiered build complete (commit 7861f8d)
- **Reorg:** scrapers moved to `sources/` (euraxess, vhio, academictransfer, lacaixa).
- **AcademicTransfer:** public Bearer token extracted live from the Nuxt payload;
  `function_types=9` = PhD; 198 NL PhD → 16 life-science. Tier 2.
- **la Caixa:** INPhINIT Incoming/Retaining as tracked annual calls (Tier 1).
- **run.py:** builds Tier 1 (`msca_doctoral_positions.*`, 50 rows = 48 EURAXESS
  + 2 la Caixa + VHIO-as-available) and Tier 2 (`netherlands_phd.*`, 16); each
  tier writes only valid data; `source` column added.
- **report.py:** two HTML reports + annual-deadlines section.
- **Reports published:** Tier 1 https://claude.ai/artifact/SkFqVNbr4FDREeiDBnkoBu ,
  Tier 2 https://claude.ai/artifact/RgZkqWzQ3yvAbTir4CviUp

### Wed, 21 Oct 2026 — Tier 3: industry PhD (commit ee1fa2a)
- Generalised EURAXESS scraper to accept custom facets + optional funding
  validation. `sources/industry.py` uses the organisation-type facet
  (533 Large Enterprise + 537 SME/Start-up) with R1, no funding restriction.
- 24 R1 industry positions -> 11 life-science -> 9 in the 7 countries.
- `data/industry_phd.*`; third report https://claude.ai/artifact/AgrBbb6uNrm36AYufhnbzx

### Wed, 21 Oct 2026 — Annual-deadline status (A) + combined report
- `report.py` now also writes `scholarships_report.html` (tabbed: Tier 1/2/3 +
  deadlines). Combined artifact https://claude.ai/artifact/4PgcqNCFhkNUeNS3kRBawC
- `sources/deadlines.py`: each run estimates open/upcoming status per scheme
  from today's date (date math, no scraping). `data/annual_deadlines_status.json`.
- **Live check (B) not feasible:** la Caixa 403-blocks bots; EMBL has no stable
  status page. A browser can't run in the weekly cron, so status stays estimated.
  (la Caixa INPhINIT is MSCA-COFUND funded, so its host positions still flow
  through the Tier-1 EURAXESS scrape when present.)

### Mon, 27 Oct 2026 — France (Montpellier/Lyon) tracker
- New sources/france.py: EURAXESS France (filtered by city — parse_card now
  keeps raw work-location string) + LinkedIn public guest search; PhD +
  life-science in config.FRANCE_CITIES. Added `city` column, build_france step,
  France tab in combined report. First run: 6 (5 EURAXESS + 1 LinkedIn).
- Fixed: data/netherlands_phd.* had unresolved git conflict markers (a merge
  ran without merge.ours.driver) which broke report.py; regenerated cleanly.

### Wed, 28 Oct 2026 — doctorat.gouv.fr, cancer radar, drop Netherlands
- Added app.doctorat.gouv.fr (French national doctoral portal, JSON API
  /api/propositions-these) to the France tracker. France now 19.
- New sources/cancer_radar.py: every PhD from 25+5 curated cancer institutes
  (Spain & France), matched by institute alias. Sources: doctorat.gouv.fr +
  EURAXESS Spain + VHIO. data/cancer_centres_radar.*; "Cancer centres" tab +
  `centre` column. First run: 12 across 6 centres (CRCL, IUCT, CNIO, IRB, VHIO, IMIM).
  Artifact https://claude.ai/artifact/CRAzaekWV6bvTP32FRCNqr
- Removed Tier 2 (Netherlands / AcademicTransfer) entirely at user request.
  NOTE: Netherlands is still one of the 7 Tier-1 COUNTRIES_FILTER countries.

## Outstanding / Next
- (Optional) GitHub Pages so the hosted reports auto-refresh weekly.
- la Caixa deadlines are *expected* windows — verify against official pages yearly.
- AcademicTransfer relies on a public token extracted at runtime (robust to
  rotation, but watch for API changes).
