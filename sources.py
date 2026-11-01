"""Récupération des offres : France Travail (API officielle) et Welcome to the Jungle."""
import os
import time
from datetime import datetime, timezone

import httpx

import config
import wttj_scraper as w

FT_TOKEN_URL = "https://entreprise.francetravail.fr/connexion/oauth2/access_token?realm=/partenaire"
FT_SEARCH_URL = "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"
FT_PAGE = 150


def _ft_token(client: httpx.Client) -> str:
    r = client.post(
        FT_TOKEN_URL,
        data={
            "grant_type": "client_credentials",
            "client_id": os.environ["FT_CLIENT_ID"],
            "client_secret": os.environ["FT_CLIENT_SECRET"],
            "scope": "api_offresdemploiv2 o2dsoffre",
        },
    )
    r.raise_for_status()
    return r.json()["access_token"]


def fetch_france_travail() -> list[dict]:
    offers: dict[str, dict] = {}
    with httpx.Client(timeout=30) as client:
        headers = {"Authorization": f"Bearer {_ft_token(client)}"}
        for query in config.FT_QUERIES:
            start = 0
            while start < config.FT_MAX_PER_QUERY:
                end = min(start + FT_PAGE, config.FT_MAX_PER_QUERY) - 1
                params = {
                    "motsCles": query,
                    "region": config.FT_REGION,
                    "publieeDepuis": config.FT_DAYS,
                    "sort": 1,
                    "range": f"{start}-{end}",
                }
                r = client.get(FT_SEARCH_URL, params=params, headers=headers)
                if r.status_code == 204:
                    break
                r.raise_for_status()
                batch = r.json().get("resultats", [])
                for o in batch:
                    oid = f"ft:{o['id']}"
                    if oid in offers:
                        continue
                    offers[oid] = {
                        "id": oid,
                        "source": "France Travail",
                        "title": (o.get("intitule") or "").strip(),
                        "company": (o.get("entreprise") or {}).get("nom", ""),
                        "location": (o.get("lieuTravail") or {}).get("libelle", ""),
                        "contract": o.get("typeContrat", ""),
                        "salary": (o.get("salaire") or {}).get("libelle", ""),
                        "remote": "",
                        "published": (o.get("dateCreation") or "")[:10],
                        "url": f"https://candidat.francetravail.fr/offres/recherche/detail/{o['id']}",
                        "snippet": (o.get("description") or "")[:300].replace("\n", " "),
                        "text": (o.get("description") or "")
                        + " "
                        + " ".join(c.get("libelle", "") for c in (o.get("competences") or [])),
                        "experience": o.get("experienceLibelle", ""),
                    }
                if len(batch) < end - start + 1:
                    break
                start += FT_PAGE
                time.sleep(0.4)
            print(f"[France Travail] {query!r} -> {len(offers)} offres cumulées")
            time.sleep(0.4)
    return list(offers.values())


def _loc(v) -> str:
    """Champ WTTJ parfois sous forme {"fr": "...", "en": "..."}."""
    if isinstance(v, dict):
        return _loc(v.get("fr") or next(iter(v.values()), ""))
    return v if isinstance(v, str) else ""


def fetch_wttj() -> list[dict]:
    offers: dict[str, dict] = {}
    with httpx.Client() as client:
        for query in config.WTTJ_QUERIES:
            hits = w.paginate(client, w.JOBS_INDEX, query, max_pages=config.WTTJ_MAX_PAGES)
            for h in hits:
                office = h.get("office") or {}
                remote = h.get("remote") or ""
                if office.get("state") != config.WTTJ_STATE and remote != "fulltime":
                    continue
                row = w.job_to_row(h, query, {})
                if not row["job_url"]:
                    continue
                oid = f"wttj:{row['raw_id']}"
                if oid in offers:
                    continue
                offers[oid] = {
                    "id": oid,
                    "source": "WTTJ",
                    "title": row["job_title"],
                    "company": row["company_name"],
                    "location": row["location"],
                    "contract": row["contract_type"],
                    "salary": "",
                    "remote": {"fulltime": "Télétravail complet", "partial": "Télétravail partiel"}.get(remote, ""),
                    "published": (row["published_at"] or "")[:10],
                    "url": row["job_url"],
                    "snippet": row["description"][:300],
                    "text": w.strip_html(h.get("profile", "")) + " " + _loc(h.get("profession_name")),
                    "experience": "",
                }
    return list(offers.values())


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")
