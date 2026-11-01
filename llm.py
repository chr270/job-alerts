"""Lecture des offres par Claude (optionnelle).

Activée uniquement si la variable ANTHROPIC_API_KEY existe. Sans clé, seul le tri par règles (scoring.py) s'applique.
Coût : quelques centimes par jour (seules les nouvelles offres déjà plutôt pertinentes sont envoyées).
"""
import json
import os
import re

import httpx

MODEL = "claude-haiku-5-5"
MAX_PER_RUN = 60

PROFIL = """Christopher, ~4 ans d'expérience, Mastère Stratégie e-business. Poste actuel : chef de projets marketing digital chez Ayvens
(migration Oracle Eloqua -> Salesforce Marketing Cloud, campagnes emailing, parcours automatisés, RGPD, chatbot, reporting KPI).
Avant : Traffic Manager (SEO, SEA, Meta Ads, retargeting) chez Place des Tendances (Printemps) et chargé de mission marketing e-commerce.
Outils : SFMC, Salesforce, Eloqua, Google Analytics, GTM, Looker Studio, Power BI, n8n/Make/Zapier, Webflow/WordPress/Shopify, Jira, IA (Claude, ChatGPT, Copilot).
Cherche : marketing automation / CRM, acquisition (SEO/SEA), marketing digital, MarTech ; niveau junior à confirmé (pas de poste de management d'équipe ni de direction).
Zone : Île-de-France (domicile Seine-Saint-Denis) ou télétravail complet."""


def review(offers: list[dict]) -> dict[str, dict]:
    """offers : liste de dicts avec id, title, company, text. Renvoie {id: {"ai": 0-100, "note": "..."}}."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return {}
    out: dict[str, dict] = {}
    with httpx.Client(timeout=60) as client:
        for o in offers[:MAX_PER_RUN]:
            prompt = (
                f"Profil du candidat :\n{PROFIL}\n\nOffre :\nTitre : {o['title']}\nEntreprise : {o['company']}\n"
                f"Texte : {o['text'][:3500]}\n\n"
                'Note de 0 à 100 l\'adéquation de cette offre pour ce candidat (compétences, niveau, missions). '
                'Réponds uniquement en JSON : {"score": <0-100>, "note": "<une phrase en français : pourquoi>"}'
            )
            try:
                r = client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                    json={"model": MODEL, "max_tokens": 200, "messages": [{"role": "user", "content": prompt}]},
                )
                r.raise_for_status()
                txt = r.json()["content"][0]["text"]
                data = json.loads(re.search(r"\{.*\}", txt, re.S).group(0))
                out[o["id"]] = {"ai": max(0, min(100, int(data["score"]))), "note": str(data["note"])[:240]}
            except Exception as e:  # une offre en échec ne bloque pas les autres
                print(f"[llm] {o['id']} ignorée : {e!r}")
    return out
