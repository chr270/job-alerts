"""Récupération des offres : France Travail (API officielle) et Welcome to the Jungle."""
import os
import time
from datetime import datetime, timezone

import httpx

import config
import targets
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


def _ft_offer(o: dict) -> dict:
    return {
        "id": f"ft:{o['id']}",
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


def _ft_search(client: httpx.Client, headers: dict, query: str, max_n: int) -> list[dict]:
    out, start = [], 0
    while start < max_n:
        end = min(start + FT_PAGE, max_n) - 1
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
        out.extend(_ft_offer(o) for o in batch)
        if len(batch) < end - start + 1:
            break
        start += FT_PAGE
        time.sleep(0.4)
    return out


def fetch_france_travail() -> list[dict]:
    offers: dict[str, dict] = {}
    with httpx.Client(timeout=30) as client:
        headers = {"Authorization": f"Bearer {_ft_token(client)}"}
        for query in config.FT_QUERIES:
            for o in _ft_search(client, headers, query, config.FT_MAX_PER_QUERY):
                offers.setdefault(o["id"], o)
            print(f"[France Travail] {query!r} -> {len(offers)} offres cumulées")
            time.sleep(0.4)
    return list(offers.values())


def _loc(v) -> str:
    """Champ WTTJ parfois sous forme {"fr": "...", "en": "..."}."""
    if isinstance(v, dict):
        return _loc(v.get("fr") or next(iter(v.values()), ""))
    return v if isinstance(v, str) else ""


def _wttj_offer(h: dict, query: str) -> dict | None:
    office = h.get("office") or {}
    remote = h.get("remote") or ""
    if office.get("state") != config.WTTJ_STATE and remote != "fulltime":
        return None
    row = w.job_to_row(h, query, {})
    if not row["job_url"]:
        return None
    return {
        "id": f"wttj:{row['raw_id']}",
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


def fetch_wttj() -> list[dict]:
    offers: dict[str, dict] = {}
    with httpx.Client() as client:
        for query in config.WTTJ_QUERIES:
            for h in w.paginate(client, w.JOBS_INDEX, query, max_pages=config.WTTJ_MAX_PAGES):
                o = _wttj_offer(h, query)
                if o:
                    offers.setdefault(o["id"], o)
    return list(offers.values())


def fetch_targets() -> list[dict]:
    """Recherche entreprise par entreprise (liste targets.py). Ne garde que les offres de l'entreprise visée."""
    offers: dict[str, dict] = {}
    with httpx.Client(timeout=30) as client:
        headers = {"Authorization": f"Bearer {_ft_token(client)}"}
        for name in targets.NAMES:
            # France Travail : "<entreprise> marketing" et "<entreprise> CRM"
            for extra in ("marketing", "CRM"):
                try:
                    for o in _ft_search(client, headers, f"{name} {extra}", FT_PAGE):
                        if targets.match(o["company"]) == name:
                            offers.setdefault(o["id"], o)
                except httpx.HTTPError as e:
                    print(f"[cibles] FT {name!r} ignorée : {e!r}")
                time.sleep(0.35)
            # WTTJ : la requête par nom ramène les offres de cette entreprise
            try:
                for h in w.fetch_page(client, w.JOBS_INDEX, name, 0, w.FRANCE_FILTER).get("hits", []):
                    o = _wttj_offer(h, name)
                    if o and targets.match(o["company"]) == name:
                        offers.setdefault(o["id"], o)
            except (httpx.HTTPError, SystemExit) as e:
                print(f"[cibles] WTTJ {name!r} ignorée : {e!r}")
            time.sleep(0.25)
    print(f"[cibles] {len(offers)} offres d'entreprises ciblées")
    return list(offers.values())


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")
