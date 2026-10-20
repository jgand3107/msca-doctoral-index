"""
Configuration for the MSCA doctoral position scraper.

Edit this file to change *what* gets scraped. The values are EURAXESS
taxonomy term IDs, taken straight from the portal's own filter controls.
"""

# Base EURAXESS jobs search endpoint (server-rendered, GET-based facets).
BASE_URL = "https://euraxess.ec.europa.eu/jobs/search"
SITE_ROOT = "https://euraxess.ec.europa.eu"

# --- Researcher profile --------------------------------------------------
# 447 = First Stage Researcher (R1)  -> this is what excludes postdocs.
# (448 = R2 recognised / postdoc, 449 = R3, 450 = R4)
RESEARCHER_PROFILE = 447

# --- Funding programmes --------------------------------------------------
# Which EU funding programmes count as "MSCA doctoral".
# Field on the portal is (confusingly) named "job_is_eu_founded".
#   4348 = Horizon Europe - MSCA        (MSCA Doctoral Networks etc.)
#   4349 = Horizon Europe - COFUND      (co-funded doctoral programmes)
#   6051 = Horizon 2020                 (legacy; add if you want older MSCA)
FUNDING_PROGRAMMES = {
    4348: "Horizon Europe - MSCA",
    4349: "Horizon Europe - COFUND",
    # 6051: "Horizon 2020",   # uncomment to include legacy H2020 MSCA
}

# --- Politeness / robustness --------------------------------------------
REQUEST_DELAY_SECONDS = 1.0        # pause between page requests
REQUEST_TIMEOUT = 60               # per-request timeout (seconds)
MAX_RETRIES = 3                    # retries on transient network errors
USER_AGENT = (
    "msca-doctoral-scraper/1.0 "
    "(weekly research index of MSCA PhD positions; contact via GitHub repo)"
)

# Safety cap so a portal change can never spin forever.
MAX_PAGES = 100

# --- Detail-page enrichment ---------------------------------------------
# Each listing links to /jobs/<id>, whose detail page carries contract type,
# weekly hours, required education level, the Marie Curie grant number, and
# (rarely) an offer start date. Enabling this fetches one extra page per
# listing. Detail URLs occasionally redirect to the search page; the scraper
# probes a few first and skips the whole batch if the portal is redirecting
# everything, so a run never fails because of it.
# Set to False for a much faster run that keeps every listing column + dates.
ENRICH_DETAILS = True

# --- Output --------------------------------------------------------------
OUTPUT_DIR = "data"
CSV_FILE = "msca_doctoral_positions.csv"
JSON_FILE = "msca_doctoral_positions.json"
META_FILE = "last_run.json"
