# MSCA Doctoral Positions — weekly index

A small, free, self-updating index of **MSCA doctoral (PhD) positions** advertised
on the [EURAXESS jobs portal](https://euraxess.ec.europa.eu/jobs/search). It scrapes
every matching listing once a week and publishes a tidy table of the important dates
(when it **opened**, when it **closes**, and — when the portal exposes it — the
**start date**), ready to read straight into R or Python.

> **Scope:** first-stage researchers (R1 — i.e. *doctoral candidates, not postdocs*)
> funded by **Horizon Europe – MSCA** and **Horizon Europe – COFUND** doctoral
> programmes, **filtered to life-science fields only** (social sciences,
> humanities, and non-life fields such as pure engineering/physics/CS are
> dropped). That narrows ~215 MSCA+COFUND doctoral posts to ~75 life-science
> ones. Edit [`config.py`](config.py) to change the scope or the field filter
> (set `LIFE_SCIENCES_ONLY = False` to keep every field).

---

## Sources & tiers

This is a **multi-source** tracker. Each row carries a `source` column.

**Tier 1 — main** (`data/msca_doctoral_positions.*`):
- **EURAXESS** MSCA + COFUND doctoral (R1, life-science, 7 countries: ES, FR, UK, DE, IT, NL, CH)
- **VHIO** (Vall d'Hebron Institute of Oncology) — predoctoral/PhD listings only (no postdoc)
- **la Caixa** INPhINIT doctoral fellowships — tracked annual calls (expected deadlines)

**Tier 2 — Netherlands** (`data/netherlands_phd.*`):
- **AcademicTransfer** — life-science PhD vacancies in the Netherlands (via its public API)

**Annual deadlines** (`data/annual_deadlines.csv`): curated big recurring schemes
(MSCA, EMBL, Boehringer, la Caixa, FPI/FPU, UKRI DTPs, Max Planck IMPRS, Pasteur
PPU, ETH/EPFL, SNSF…) with expected windows and official links.

Code is organised under [`sources/`](sources/) (`euraxess.py`, `vhio.py`,
`academictransfer.py`, `lacaixa.py`); [`run.py`](run.py) orchestrates the tiers
and [`report.py`](report.py) builds the HTML reports.

## What you get

Regenerated on every run, in [`data/`](data/):

| File | Use |
|------|-----|
| `msca_doctoral_positions.csv` / `.json`  | **Tier 1** main table (read into R / Excel / pandas) |
| `netherlands_phd.csv` / `.json` | **Tier 2** Netherlands life-science PhD |
| `annual_deadlines.csv` | Recurring-scheme calendar |

### Columns

| Column | Meaning |
|--------|---------|
| `id` | EURAXESS job id |
| `title` | Position title |
| `programme_type` | `MSCA`, `COFUND`, or `H2020` |
| `funding_programme` | Full programme label from the portal |
| `researcher_profile` | Always *First Stage Researcher (R1)* |
| `organisation` | Coordinating organisation |
| `host_institution`, `country` | Where the post is based (best-effort) |
| `research_field` | Portal research field(s) |
| `number_of_offers` | How many posts the listing covers |
| **`open_date`** | When the listing was published (ISO date) |
| **`deadline`** | Application deadline (ISO datetime, with timezone) |
| `deadline_display` | Human-readable deadline incl. local timezone |
| **`start_date`** | Offer start date — *rarely published by EURAXESS*, see note |
| `employment_type` | Type of contract (from detail page) |
| `hours_per_week` | Weekly hours (from detail page) |
| `education_level` | Required education level (from detail page) |
| `grant_agreement_number` | Marie Skłodowska-Curie grant number (from detail page) |
| `url` | Link to the full listing |
| `detail_available` | Whether the detail page was reachable this run |
| `first_seen`, `last_seen` | Dates this script first/last saw the listing |

> **Note on `start_date`:** an offer start date lives only on each listing's
> detail page, and in practice **EURAXESS listings almost never fill in that
> field** for MSCA positions — most state timing only in free-text (e.g. "as
> soon as possible"). The scraper reads it whenever a listing does publish it,
> but expect this column to be mostly empty. **`open_date` and `deadline` come
> straight from the listings and are always populated** — those are your
> reliable "when it opens / when it closes" dates.
>
> The other detail columns (`employment_type`, `hours_per_week`,
> `education_level`, `grant_agreement_number`) are filled from each listing's
> detail page. EURAXESS serves those detail pages only intermittently (it often
> 307-redirects them), so any single run enriches just a subset — but each
> weekly run **carries forward** values captured previously, so coverage
> accumulates over time rather than flickering. Set `ENRICH_DETAILS = False` in
> `config.py` to skip detail pages entirely for a much faster run (you keep all
> the listing columns and both dates).

---

## Read it into R

Once this lives in a GitHub repo (below), point R at the **raw** file URL — that URL
*is* your "API":

```r
# install.packages("readr")
url <- "https://raw.githubusercontent.com/<you>/<repo>/main/data/msca_doctoral_positions.csv"
jobs <- readr::read_csv(url)

# e.g. positions closing in the next 30 days
library(dplyr)
jobs |>
  mutate(deadline = as.POSIXct(deadline, tz = "UTC")) |>
  filter(deadline >= Sys.time(), deadline <= Sys.time() + 30*24*3600) |>
  arrange(deadline) |>
  select(title, country, organisation, open_date, deadline, url)
```

Python:

```python
import pandas as pd
df = pd.read_csv("https://raw.githubusercontent.com/<you>/<repo>/main/data/msca_doctoral_positions.csv")
```

---

## Run it locally

```bash
pip install -r requirements.txt
python run.py                # full scrape (listings + best-effort detail)
python run.py --no-details   # listings only, faster
```

Output lands in `data/`.

---

## Put it on GitHub (free weekly updates)

The repo includes a GitHub Actions workflow
([`.github/workflows/weekly.yml`](.github/workflows/weekly.yml)) that runs the
scraper **every Monday at 06:00 UTC** in GitHub's cloud and commits the refreshed
`data/` files. No server of your own required.

One-time setup:

1. Create a new **empty** repo on GitHub (e.g. `msca-doctoral-index`).
2. From this folder:
   ```bash
   git init
   git add .
   git commit -m "Initial commit: MSCA doctoral scraper"
   git branch -M main
   git remote add origin https://github.com/<you>/<repo>.git
   git push -u origin main
   ```
3. On GitHub: **Settings → Actions → General → Workflow permissions →** select
   **Read and write permissions** (lets the weekly job commit the data back).
4. (Optional) Trigger the first run now: **Actions → "Weekly MSCA doctoral
   scrape" → Run workflow**.

That's it. Each week the table refreshes itself and the raw CSV URL stays current.

---

## Reliability note (why there are two runners)

EURAXESS intermittently serves **degraded/unfiltered pages to cloud IPs** such
as GitHub Actions — a run may get the full ~215 offers or a near-empty page.
To protect you, the scraper **validates every scrape** (profiles must be R1,
funding must match, row count must be plausible) and **refuses to overwrite the
published data with a degraded result** — a bad run fails loudly and the last
good data stays live. It also retries up to 8 times per run to ride out the bad
windows.

Because of that cloud flakiness there are two runners:

- **GitHub Actions** (`.github/workflows/weekly.yml`) — free, hands-off, runs
  weekly in the cloud. Updates when EURAXESS cooperates; otherwise skips.
- **Local weekly task** (`run_and_push.ps1` + Windows Task Scheduler) — runs on
  your own machine, where EURAXESS always returns full results, and pushes the
  update. This is the reliable one. It's registered as the scheduled task
  **"MSCA Doctoral Weekly Scrape"** (weekly, Mondays 09:00, catches up if the PC
  was off). Run it any time by hand:
  ```powershell
  powershell -ExecutionPolicy Bypass -File run_and_push.ps1
  ```
  Output is logged to `weekly_run.log`.

## Changing what's scraped

Everything tunable is in [`config.py`](config.py):

- `RESEARCHER_PROFILE` — `447` = R1 (doctoral). Change to include other profiles.
- `FUNDING_PROGRAMMES` — add/remove EU programmes by their taxonomy id
  (the file lists the known ids, including legacy Horizon 2020).
- `LIFE_SCIENCES_ONLY` / `LIFE_SCIENCE_KEYWORDS` — the field filter. Turn the
  filter off, or edit the keyword list to add fields (e.g. `"environmental
  science"`, `"chemistry"`, `"psycholog"`) or make it stricter.
- `REQUEST_DELAY_SECONDS` — politeness delay between page requests.
- `ENRICH_DETAILS` — set `False` to skip detail-page fetching entirely.

## How it works

EURAXESS's search is a server-rendered page whose filters are plain URL
parameters, so the scraper just requests:

```
/jobs/search?f[0]=job_research_profile:447&f[1]=job_is_eu_founded:4348&f[2]=job_is_eu_founded:4349&page=N
```

walks the pages, parses each result card, and (best-effort) each detail page.
No API key, login, or browser automation is involved.
