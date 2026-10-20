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

# EURAXESS intermittently serves degraded pages to cloud IPs (e.g. GitHub
# Actions). A degraded scrape is rejected and the whole scrape is retried
# with a fresh session; these control how hard/long we try before giving up.
SCRAPE_ATTEMPTS = 8                # full-scrape attempts before aborting
RETRY_BACKOFF_SECONDS = 30         # base wait between attempts (grows per try)
# A realistic browser UA: EURAXESS sometimes serves degraded/unfiltered pages
# to obvious bots, so we present as a normal desktop browser.
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# Safety cap so a portal change can never spin forever.
MAX_PAGES = 100

# --- Field filter (life sciences only) ----------------------------------
# EURAXESS tags each position with research fields. With this on, a position
# is kept only if ANY of its field tags matches one of the keywords below
# (case-insensitive substring). That keeps life-science posts — including
# interdisciplinary ones like biophysics, biomedical engineering, or
# computational biology — and drops social sciences, humanities, and non-life
# fields (pure engineering, physics, maths, computer science, chemistry, etc.).
# Set to False to keep every field. Edit the list to widen/narrow the net
# (e.g. add "environmental science", "chemistry", or "psycholog").
LIFE_SCIENCES_ONLY = True
LIFE_SCIENCE_KEYWORDS = [
    "biolog", "biochem", "biophys", "biotech", "biomedical",
    "biological engineering", "medical science", "medicine", "health science",
    "pharmacol", "pharmacy", "pharmaceutical", "neuroscience", "neurobiolog",
    "botany", "zoolog", "microbiolog", "genetic", "genomic", "proteomic",
    "immunolog", "virolog", "veterinary", "physiolog", "epidemiolog",
    "toxicolog", "agricultural science", "ecology", "cell biolog", "cancer",
    "molecular biolog", "bioinformatic", "life science",
]

# --- Country filter ------------------------------------------------------
# Keep only positions based in these countries (names as EURAXESS writes them;
# note the UK is "United Kingdom"). Set to None or [] to keep all countries.
COUNTRIES_FILTER = [
    "Spain", "France", "United Kingdom", "Germany", "Italy", "Netherlands",
    "Switzerland",
]

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
