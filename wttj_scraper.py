#!/usr/bin/env python3
"""
Welcome to the Jungle Scraper — Algolia search-only, read-only.

Usage:
    python wttj_scraper.py "CRM" --output crm_jobs.csv
    python wttj_scraper.py "CRM" "SEO" "data" --output all_jobs.csv
    python wttj_scraper.py "CRM" --max-pages 2 --output test.csv  # testing
"""

import argparse
import csv
import html
import re
import sys
import time
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import quote

import httpx

# ── Algolia config (public search-only key from WTTJ frontend) ──────────────
ALGOLIA_APP_ID = "CSEKHVMS53"
ALGOLIA_API_KEY = "4bd8f6215d0cc52b26430765769e65a0"
ALGOLIA_ENDPOINT = f"https://{ALGOLIA_APP_ID}-dsn.algolia.net/1/indexes/*/queries"
JOBS_INDEX = "wk_cms_jobs_production"
ORGS_INDEX = "wk_cms_organizations_production"
FRANCE_FILTER = "website.reference:wttj_fr"
HITS_PER_PAGE = 100
MAX_RESULTS = 1000  # Algolia hard cap
RATE_LIMIT_DELAY = 0.25  # seconds between paginated calls

HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded",
    "X-Algolia-API-Key": ALGOLIA_API_KEY,
    "X-Algolia-Application-Id": ALGOLIA_APP_ID,
    "Referer": "https://www.welcometothejungle.com/",
}

CSV_COLUMNS = [
    "job_query", "company_name", "company_url", "industry", "location",
    "country", "description", "website", "linkedin", "logo_url",
    "employee_count", "jobs_count", "job_title", "job_url", "contract_type",
    "remote_policy", "published_at", "raw_id", "source_url", "scraped_at",
]


def strip_html(text: str) -> str:
    """Remove HTML tags and decode entities, keep plain text."""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def fetch_page(
    client: httpx.Client, index_name: str, query: str, page: int, filters: str
) -> dict:
    """Fetch one page of results from an Algolia index."""
    params = f"hitsPerPage={HITS_PER_PAGE}&page={page}&query={quote(query)}&filters={quote(filters)}"
    payload = {"requests": [{"indexName": index_name, "params": params}]}
    resp = client.post(ALGOLIA_ENDPOINT, headers=HEADERS, content=str(payload).replace("'", '"'), timeout=30)

    if resp.status_code == 403:
        print(f"ERROR 403: {resp.json().get('message', 'Forbidden')}", file=sys.stderr)
        print(
            "The API key may be expired or the referer check changed. "
            "Update the key manually — do not try to bypass.",
            file=sys.stderr,
        )
        sys.exit(1)
    if resp.status_code != 200:
        print(f"ERROR {resp.status_code}: {resp.text[:500]}", file=sys.stderr)
        sys.exit(1)

    return resp.json()["results"][0]


def paginate(
    client: httpx.Client, index_name: str, query: str, max_pages: Optional[int] = None
) -> list[dict]:
    """Fetch all pages for a query, respecting the 1000-result cap."""
    all_hits: list[dict] = []
    seen_ids: set[str] = set()
    page = 0
    filters = FRANCE_FILTER

    while True:
        result = fetch_page(client, index_name, query, page, filters)
        nb_hits = result.get("nbHits", 0)
        hits = result.get("hits", [])

        if not hits:
            break

        for hit in hits:
            oid = hit.get("reference") or hit.get("objectID")
            if oid not in seen_ids:
                seen_ids.add(oid)
                all_hits.append(hit)

        print(f"  Page {page + 1}: got {len(hits)} hits (total collected: {len(all_hits)} / {nb_hits})")

        # Check 1000 cap
        if (page + 1) * HITS_PER_PAGE >= MAX_RESULTS:
            print(
                f"  ⚠ Algolia 1000-result cap reached ({len(all_hits)} collected). "
                f"Try adding filters (sector, city, date) for the remaining results.",
                file=sys.stderr,
            )
            break

        if max_pages and page + 1 >= max_pages:
            break

        if len(all_hits) >= nb_hits:
            break

        page += 1
        time.sleep(RATE_LIMIT_DELAY)

    return all_hits


def fetch_org_jobs_counts(
    client: httpx.Client, org_slugs: set[str]
) -> dict[str, int]:
    """Batch-fetch jobs_count for organizations by slug.

    Uses a multi-query to look up orgs in one or few calls.
    """
    if not org_slugs:
        return {}

    counts: dict[str, int] = {}
    slug_list = list(org_slugs)

    # Process in batches of 10 orgs per query (Algolia query length limit)
    for i in range(0, len(slug_list), 10):
        batch = slug_list[i : i + 10]
        requests = []
        for slug in batch:
            requests.append({
                "indexName": ORGS_INDEX,
                "params": f"hitsPerPage=1&page=0&query={quote(slug)}&filters={quote(FRANCE_FILTER)}",
            })

        payload = {"requests": requests}
        resp = client.post(
            ALGOLIA_ENDPOINT,
            headers=HEADERS,
            content=str(payload).replace("'", '"'),
            timeout=30,
        )

        if resp.status_code != 200:
            continue

        for result in resp.json().get("results", []):
            hits = result.get("hits", [])
            if hits:
                hit = hits[0]
                slug = hit.get("slug", "")
                counts[slug] = hit.get("jobs_count", 0)

        if i + 10 < len(slug_list):
            time.sleep(RATE_LIMIT_DELAY)

    return counts


def job_to_row(hit: dict, keyword: str, org_jobs_counts: dict[str, int]) -> dict:
    """Convert an Algolia job hit to a CSV row dict."""
    org = hit.get("organization", {})
    org_slug = org.get("slug", "")
    org_name = org.get("name", "")
    office = hit.get("office") or {}
    sectors = hit.get("sectors") or []

    # Industry from first sector
    industry = ""
    if sectors:
        parent = sectors[0].get("parent", {})
        industry = parent.get("fr", "")

    # Build URLs
    company_url = f"https://www.welcometothejungle.com/fr/companies/{org_slug}" if org_slug else ""
    job_url = (
        f"https://www.welcometothejungle.com/fr/companies/{org_slug}/jobs/{hit.get('slug', '')}"
        if org_slug and hit.get("slug")
        else ""
    )
    source_url = f"https://www.welcometothejungle.com/fr/jobs?query={quote(keyword)}"

    return {
        "job_query": keyword,
        "company_name": org_name,
        "company_url": company_url,
        "industry": industry,
        "location": office.get("city", ""),
        "country": office.get("country", ""),
        "description": strip_html(hit.get("profile", ""))[:500],
        "website": "",  # not in Algolia
        "linkedin": "",  # not in Algolia
        "logo_url": org.get("logo", {}).get("url", ""),
        "employee_count": org.get("nb_employees", ""),
        "jobs_count": org_jobs_counts.get(org_slug, ""),
        "job_title": hit.get("name", ""),
        "job_url": job_url,
        "contract_type": (hit.get("contract_type_names") or {}).get("fr", ""),
        "remote_policy": hit.get("remote", ""),
        "published_at": hit.get("published_at", ""),
        "raw_id": hit.get("reference", ""),
        "source_url": source_url,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
    }


def scrape_keywords(
    keywords: list[str],
    output_path: str,
    max_pages: Optional[int] = None,
) -> int:
    """Scrape multiple keywords, deduplicate, and export to CSV."""
    all_rows: list[dict] = []
    seen_job_ids: set[str] = set()
    all_org_slugs: set[str] = set()

    with httpx.Client() as client:
        for kw in keywords:
            print(f"\n🔍 Searching: \"{kw}\"")
            hits = paginate(client, JOBS_INDEX, kw, max_pages=max_pages)
            print(f"  → {len(hits)} unique jobs for \"{kw}\"")

            for hit in hits:
                rid = hit.get("reference", "")
                if rid in seen_job_ids:
                    continue
                seen_job_ids.add(rid)

                org_slug = hit.get("organization", {}).get("slug", "")
                if org_slug:
                    all_org_slugs.add(org_slug)

                all_rows.append((kw, hit))

        # Batch-fetch org details for jobs_count
        print(f"\n🏢 Fetching org details for {len(all_org_slugs)} companies...")
        org_jobs_counts = fetch_org_jobs_counts(client, all_org_slugs)
        print(f"  → Got jobs_count for {len(org_jobs_counts)} orgs")

    # Build final rows
    final_rows = []
    seen_urls: set[str] = set()
    for kw, hit in all_rows:
        row = job_to_row(hit, kw, org_jobs_counts)
        job_url = row["job_url"]
        if job_url in seen_urls:
            continue
        seen_urls.add(job_url)
        final_rows.append(row)

    # Write CSV
    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(final_rows)

    print(f"\n✅ Exported {len(final_rows)} rows to {output_path}")
    return len(final_rows)


def main():
    parser = argparse.ArgumentParser(
        description="Welcome to the Jungle job scraper (read-only, Algolia search API)"
    )
    parser.add_argument(
        "keywords", nargs="+", help="Search keyword(s), e.g. CRM marketing"
    )
    parser.add_argument(
        "--output", "-o", default="wttj_jobs.csv", help="Output CSV file path"
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Max pages per keyword (for testing, default: unlimited up to Algolia cap)",
    )
    args = parser.parse_args()

    scrape_keywords(args.keywords, args.output, max_pages=args.max_pages)


if __name__ == "__main__":
    main()