"""
Core scraping logic for MSCA doctoral (R1) positions on the EURAXESS jobs portal.

The portal is a server-rendered OpenEuropa "list page". Results are reachable
with plain GET requests using facet parameters of the form:

    ?f[0]=job_research_profile:447&f[1]=job_is_eu_founded:4348&f[2]=job_is_eu_founded:4349&page=N

so no browser, login, or JavaScript is required for the listings themselves.

Only the Python standard library + requests + beautifulsoup4 are used
(html.parser, so there is no compiled-dependency / lxml install headache).
"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

import config

# Labels that appear inside each result card, in no guaranteed order.
_CARD_LABELS = [
    "Posted on:",
    "Department:",
    "Work Locations:",
    "Research Field:",
    "Researcher Profile:",
    "Funding Programme:",
    "Application Deadline:",
]


# --------------------------------------------------------------------------
# HTTP helpers
# --------------------------------------------------------------------------
def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": config.USER_AGENT,
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": ("text/html,application/xhtml+xml,application/xml;q=0.9,"
                   "image/avif,image/webp,*/*;q=0.8"),
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    })
    # Pre-accept the EC cookie-consent so EURAXESS serves full content.
    s.cookies.set(
        "cck1",
        "%7B%22cm%22%3Atrue%2C%22all1st%22%3Atrue%2C%22closed%22%3Atrue%7D",
        domain=".europa.eu",
    )
    return s


def _get(session: requests.Session, url: str, *, allow_redirects: bool = True):
    """GET with simple retry/backoff on transient failures."""
    last_exc = None
    for attempt in range(1, config.MAX_RETRIES + 1):
        try:
            resp = session.get(
                url,
                timeout=config.REQUEST_TIMEOUT,
                allow_redirects=allow_redirects,
            )
            return resp
        except requests.RequestException as exc:  # network blip, timeout, etc.
            last_exc = exc
            time.sleep(min(2 ** attempt, 10))
    raise last_exc  # exhausted retries


# --------------------------------------------------------------------------
# URL construction
# --------------------------------------------------------------------------
def default_facets() -> list[str]:
    """The MSCA/COFUND facet set (profile R1 + funding programmes)."""
    facets = [f"job_research_profile:{config.RESEARCHER_PROFILE}"]
    for term_id in config.FUNDING_PROGRAMMES:
        facets.append(f"job_is_eu_founded:{term_id}")
    return facets


def build_search_url(page: int = 0, facets: list[str] | None = None) -> str:
    """Build a faceted search URL. `facets` is a list of 'name:value' strings."""
    if facets is None:
        facets = default_facets()
    parts = []
    for i, facet in enumerate(facets):
        # f[i]=<facet>  -> url-encode the brackets and the colon value
        parts.append(f"f%5B{i}%5D={quote(facet, safe='')}")
    if page:
        parts.append(f"page={page}")
    return f"{config.BASE_URL}?{'&'.join(parts)}"


# --------------------------------------------------------------------------
# Parsing helpers
# --------------------------------------------------------------------------
def _clean(text: str | None) -> str:
    if not text:
        return ""
    # Drop stray bullet / replacement chars the portal injects between values.
    text = text.replace("�", " ").replace("»", ">")
    return re.sub(r"\s+", " ", text).strip()


def _extract_block(lines: list[str], label: str) -> str:
    """
    Return the value for `label` from a card's line list.

    Handles both inline labels ("Posted on: 19 October 2026") and
    labels whose value sits on the following line(s), stopping at the
    next known label.
    """
    others = [l for l in _CARD_LABELS if l != label]
    for idx, line in enumerate(lines):
        if line.startswith(label):
            inline = line[len(label):].strip()
            if inline:
                return _clean(inline)
            # value is on subsequent lines until the next label
            collected = []
            for nxt in lines[idx + 1:]:
                if any(nxt.startswith(o) for o in others):
                    break
                collected.append(nxt)
            return _clean(" ".join(collected))
    return ""


def _parse_posted_date(raw: str) -> str:
    """'19 October 2026' -> '2026-10-19' (ISO date)."""
    raw = raw.strip()
    for fmt in ("%d %B %Y", "%d %b %Y"):
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue
    return ""


def _programme_type(funding_label: str) -> str:
    low = funding_label.lower()
    if "msca" in low:
        return "MSCA"
    if "cofund" in low:
        return "COFUND"
    if "2020" in low:
        return "H2020"
    return ""


def _split_work_location(raw: str) -> dict:
    """
    'Number of offers: 1, Sweden, Karolinska Institutet' ->
        {offers: '1', country: 'Sweden', host: 'Karolinska Institutet'}
    Best-effort; the portal's formatting varies.
    """
    out = {"offers": "", "country": "", "host_institution": ""}
    if not raw:
        return out
    offers_m = re.search(r"Number of offers:\s*([0-9]+)", raw)
    if offers_m:
        out["offers"] = offers_m.group(1)
    # strip the "Number of offers: N," prefix, then split remaining by comma
    rest = re.sub(r"Number of offers:\s*[0-9]+\s*,?", "", raw).strip(" ,")
    bits = [b.strip() for b in rest.split(",") if b.strip()]
    if bits:
        out["country"] = bits[0]
    if len(bits) > 1:
        out["host_institution"] = bits[1]
    return out


def parse_card(card) -> dict | None:
    """Parse one `.ecl-content-item` result card into a record dict."""
    title_a = card.find("a", href=re.compile(r"/jobs/\d+"))
    if not title_a:
        return None
    href = title_a.get("href", "")
    job_id_m = re.search(r"/jobs/(\d+)", href)
    if not job_id_m:
        return None
    job_id = job_id_m.group(1)
    url = href if href.startswith("http") else config.SITE_ROOT + href

    # organisation (coordinator) anchor
    org = ""
    org_a = card.find("a", href=re.compile(r"/partnering/organisations/"))
    if org_a:
        org = _clean(org_a.get_text())

    lines = [
        l.strip()
        for l in card.get_text("\n", strip=True).split("\n")
        if l.strip()
    ]

    posted = _parse_posted_date(_extract_block(lines, "Posted on:"))
    research_field = _extract_block(lines, "Research Field:")
    profile = _extract_block(lines, "Researcher Profile:")
    funding = _extract_block(lines, "Funding Programme:")
    work_raw = _extract_block(lines, "Work Locations:")
    loc = _split_work_location(work_raw)

    # Application deadline: the single <time> element in the card.
    deadline_iso, deadline_display = "", ""
    time_el = card.find("time")
    if time_el:
        deadline_iso = time_el.get("datetime", "") or ""
        deadline_display = _clean(time_el.get_text())

    return {
        "source": "EURAXESS",
        "id": job_id,
        "title": _clean(title_a.get_text()),
        "organisation": org,
        "host_institution": loc["host_institution"],
        "country": loc["country"],
        "number_of_offers": loc["offers"],
        "research_field": research_field,
        "researcher_profile": profile,
        "funding_programme": funding,
        "programme_type": _programme_type(funding),
        "open_date": posted,                 # when it was published / opened
        "deadline": deadline_iso,            # when applications close (ISO)
        "deadline_display": deadline_display,
        "start_date": "",                    # filled by enrich_detail (rarely published)
        "employment_type": "",               # Type of Contract (from detail page)
        "hours_per_week": "",                # from detail page
        "education_level": "",               # from detail page
        "grant_agreement_number": "",        # Marie Curie grant number (from detail page)
        "url": url,
        "detail_available": "",              # yes/no once enrichment runs
    }


def is_life_science(research_field: str) -> bool:
    """True if any field tag matches a configured life-science keyword."""
    low = (research_field or "").lower()
    return any(kw in low for kw in config.LIFE_SCIENCE_KEYWORDS)


def _result_count(soup: BeautifulSoup) -> int | None:
    # The portal sometimes splits "Search results" and "(215)" into separate
    # tags, so match against the whole page text rather than a single node.
    m = re.search(r"Search results\s*\(\s*([\d,]+)\s*\)", soup.get_text(" "))
    if m:
        return int(m.group(1).replace(",", ""))
    return None


# --------------------------------------------------------------------------
# Listing scrape
# --------------------------------------------------------------------------
class ScrapeValidationError(RuntimeError):
    """Raised when a scrape result looks degraded and must not be published."""


def validate_scrape(records: list[dict], expected_total: int | None,
                    require_funding: bool = True) -> list[str]:
    """
    Return a list of problems that mean the scrape is untrustworthy.

    EURAXESS intermittently serves degraded/unfiltered pages (especially from
    cloud IPs). We must never overwrite good data with such a result, so we
    sanity-check that the facets we requested were actually applied.
    `require_funding` is False for facet sets without a funding filter
    (e.g. the industry tier, which filters by organisation type instead).
    """
    problems = []
    if not records:
        return ["zero listings parsed"]

    non_r1 = [r for r in records if "R1" not in (r.get("researcher_profile") or "")]
    if non_r1:
        problems.append(
            f"{len(non_r1)}/{len(records)} listings are not R1 "
            f"(profile facet not applied)")

    if require_funding:
        no_prog = [r for r in records if not r.get("programme_type")]
        if no_prog:
            problems.append(
                f"{len(no_prog)}/{len(records)} listings have no expected funding "
                f"programme (funding facet not applied)")

    if expected_total and len(records) < max(5, expected_total * 0.5):
        problems.append(
            f"only {len(records)} listings parsed vs portal's {expected_total}")

    return problems


def scrape_validated(session: requests.Session | None = None,
                     attempts: int | None = None,
                     verbose: bool = True,
                     facets: list[str] | None = None,
                     require_funding: bool = True) -> tuple[list[dict], int | None]:
    """
    Scrape with retries; only return a result that passes validation.

    Each attempt uses a fresh session (new cookies), and waits longer between
    tries, so a cloud run can ride out EURAXESS's degraded-response windows.
    """
    attempts = attempts or config.SCRAPE_ATTEMPTS
    problems: list[str] = []
    for attempt in range(1, attempts + 1):
        records, expected_total = scrape_listings(_session(), verbose=verbose, facets=facets)
        problems = validate_scrape(records, expected_total, require_funding=require_funding)
        if not problems:
            if verbose and attempt > 1:
                print(f"  succeeded on attempt {attempt}")
            return records, expected_total
        if verbose:
            print(f"  attempt {attempt}/{attempts} rejected: {'; '.join(problems)}")
        if attempt < attempts:
            wait = min(config.RETRY_BACKOFF_SECONDS * attempt, 90)
            if verbose:
                print(f"  waiting {wait}s before retry...")
            time.sleep(wait)
    raise ScrapeValidationError("; ".join(problems))


def scrape_listings(session: requests.Session | None = None, verbose: bool = True,
                    facets: list[str] | None = None):
    """Walk every result page; return (records, portal_reported_total)."""
    session = session or _session()
    records: dict[str, dict] = {}
    expected_total = None

    page = 0
    while page < config.MAX_PAGES:
        url = build_search_url(page, facets=facets)
        resp = _get(session, url)
        if resp.status_code != 200:
            if verbose:
                print(f"  page {page}: HTTP {resp.status_code}, stopping")
            break
        soup = BeautifulSoup(resp.text, "html.parser")

        if page == 0:
            expected_total = _result_count(soup)
            if verbose:
                print(f"  portal reports {expected_total} matching offers")

        cards = soup.select(".ecl-content-item")
        page_records = [r for r in (parse_card(c) for c in cards) if r]
        if not page_records:
            if verbose:
                print(f"  page {page}: no cards, done")
            break

        new = 0
        for rec in page_records:
            if rec["id"] not in records:
                records[rec["id"]] = rec
                new += 1
        if verbose:
            print(f"  page {page}: {len(page_records)} cards ({new} new) "
                  f"[total so far {len(records)}]")

        # If this page added nothing new, we've wrapped around the pager.
        if new == 0:
            break
        page += 1
        time.sleep(config.REQUEST_DELAY_SECONDS)

    result = list(records.values())
    if verbose and expected_total is not None and len(result) != expected_total:
        print(f"  note: collected {len(result)} vs portal's {expected_total} "
              f"(listings shift between page loads; this is normal)")
    return result, expected_total


# --------------------------------------------------------------------------
# Detail-page enrichment (best-effort)
# --------------------------------------------------------------------------
# Detail-page <dt>/<dd> labels -> record keys. EURAXESS exposes these as a
# definition list; this is far more stable than scraping JobPosting JSON-LD
# (which these listings don't include).
_DETAIL_FIELD_MAP = {
    "Offer Starting Date": "start_date",
    "Type of Contract": "employment_type",
    "Hours Per Week": "hours_per_week",
    "Education Level": "education_level",
    "Marie Curie Grant Agreement Number": "grant_agreement_number",
}


def _parse_detail_fields(soup: BeautifulSoup) -> dict:
    """Collect dt/dd pairs from the detail page into {label: value}."""
    fields: dict[str, str] = {}
    for dl in soup.find_all("dl"):
        dts = dl.find_all("dt")
        dds = dl.find_all("dd")
        for dt, dd in zip(dts, dds):
            key = _clean(dt.get_text(" "))
            if key and key not in fields:
                fields[key] = _clean(dd.get_text(" "))
    return fields


def enrich_detail(session: requests.Session, record: dict) -> dict:
    """
    Pull extra fields (contract type, hours, education level, MSCA grant
    number, and start date when published) from a listing's detail page.

    Detail URLs occasionally 307-redirect to the search page; when that
    happens we mark detail_available='no' and leave the extra fields empty.
    Note: EURAXESS rarely publishes an "Offer Starting Date", so start_date
    is usually empty even on a fully-read detail page.
    """
    try:
        resp = _get(session, record["url"], allow_redirects=True)
    except requests.RequestException:
        record["detail_available"] = "no"
        return record

    if resp.status_code != 200 or "/jobs/search" in resp.url:
        record["detail_available"] = "no"
        return record

    soup = BeautifulSoup(resp.content, "html.parser")  # bytes -> correct UTF-8
    fields = _parse_detail_fields(soup)
    for label, key in _DETAIL_FIELD_MAP.items():
        if fields.get(label):
            record[key] = fields[label]

    # Backfill the MSCA grant number from "Is the job funded..." if needed.
    record["detail_available"] = "yes" if fields else "partial"
    return record


# Detail-page availability is intermittent: individual /jobs/<id> URLs
# sometimes 307-redirect to the search page and sometimes serve fine. So we
# try every listing, but give up early only if this many requests in a row all
# redirect (which means the portal is redirecting everything right now).
_MAX_CONSECUTIVE_REDIRECTS = 12


def enrich_all(records: list[dict], session: requests.Session | None = None,
               verbose: bool = True) -> list[dict]:
    session = session or _session()
    if not records:
        return records

    consecutive_no = 0
    bailed = False
    for i, rec in enumerate(records, 1):
        enrich_detail(session, rec)
        if rec.get("detail_available") == "no":
            consecutive_no += 1
        else:
            consecutive_no = 0
        if verbose and i % 25 == 0:
            print(f"  enriched {i}/{len(records)}")
        # Portal appears to be redirecting everything; stop wasting requests.
        if consecutive_no >= _MAX_CONSECUTIVE_REDIRECTS:
            if verbose:
                print(f"  {consecutive_no} detail pages redirected in a row; "
                      f"portal not serving details now, stopping enrichment")
            for leftover in records[i:]:
                leftover["detail_available"] = "no"
            bailed = True
            break
        time.sleep(config.REQUEST_DELAY_SECONDS)

    if verbose:
        extra = sum(1 for r in records if r.get("employment_type")
                    or r.get("grant_agreement_number"))
        filled = sum(1 for r in records if r.get("start_date"))
        suffix = " (stopped early)" if bailed else ""
        print(f"  detail enrichment done{suffix}: {extra}/{len(records)} with "
              f"extra fields, {filled} with a published start date")
    return records


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
