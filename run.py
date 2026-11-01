#!/usr/bin/env python3
"""Veille quotidienne : récupère les offres, détecte les nouvelles, met à jour la page et envoie le mail.

    python run.py            # exécution normale
    python run.py --no-mail  # tout sauf l'envoi du mail
"""
import argparse
import html
import json
import os
import smtplib
import sys
from datetime import date, datetime, timedelta
from email.message import EmailMessage
from pathlib import Path

import carrieres_page
import config
import llm
import page
import scoring
import sources
import targets

ROOT = Path(__file__).parent
STATE = ROOT / "data" / "offers.json"
PAGE_FILE = ROOT / "docs" / config.PAGE_DIR / "index.html"


def load_env() -> None:
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def safe(fetch, name: str) -> list[dict] | None:
    """Une source en panne ne doit pas bloquer les autres."""
    try:
        return fetch()
    except (Exception, SystemExit) as e:  # wttj_scraper quitte avec sys.exit en cas d'erreur
        print(f"[{name}] ÉCHEC : {e!r}", file=sys.stderr)
        return None


def build_mail(new: list[dict], total: int, first_run: bool, others: int = 0) -> EmailMessage:
    new = sorted(new, key=lambda o: (o.get("score", 0), o.get("published", "")), reverse=True)
    shown = new[:60]
    title = (
        f"Veille emploi : {total} offres suivies (première synchronisation)"
        if first_run
        else f"{len(new)} nouvelle{'s' if len(new) > 1 else ''} offre{'s' if len(new) > 1 else ''} d'emploi"
    )
    rows, text = [], [title, "", f"Toutes les offres : {config.PAGE_URL}", ""]
    for o in shown:
        meta = " · ".join(x for x in [f"{o.get('score', 0)}/100", o["company"], o["location"], o["contract"], o["source"]] if x)
        if o.get("note"):
            meta += f" — {o['note']}"
        rows.append(
            f'<li style="margin-bottom:10px"><a href="{html.escape(o["url"])}"><b>{html.escape(o["title"])}</b></a>'
            f'<br><span style="color:#667085">{html.escape(meta)}</span></li>'
        )
        text.append(f"- {o['title']} | {meta}\n  {o['url']}")
    rest = (len(new) - len(shown)) + others
    more = f"<p>… et {rest} autres offres moins pertinentes, sur la page.</p>" if rest > 0 else ""
    body = (
        f'<h2 style="margin:0 0 8px">{html.escape(title)}</h2>'
        f'<p><a href="{config.PAGE_URL}">Ouvrir la page avec toutes les offres</a></p>'
        f'<ul style="padding-left:18px">{"".join(rows)}</ul>{more}'
    )
    msg = EmailMessage()
    msg["Subject"] = title
    msg["From"] = os.environ["MAIL_FROM"]
    msg["To"] = os.environ["MAIL_TO"]
    msg.set_content("\n".join(text))
    msg.add_alternative(f"<html><body>{body}</body></html>", subtype="html")
    return msg


def send(msg: EmailMessage) -> None:
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as s:
        s.login(os.environ["MAIL_FROM"], os.environ["GMAIL_APP_PASSWORD"])
        s.send_message(msg)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-mail", action="store_true")
    args = ap.parse_args()
    load_env()

    today = date.today().isoformat()
    store: dict[str, dict] = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    first_run = not store

    ft = safe(sources.fetch_france_travail, "France Travail")
    wt = safe(sources.fetch_wttj, "WTTJ")
    if ft is None and wt is None:
        print("Aucune source disponible, abandon.", file=sys.stderr)
        return 1

    tg = safe(sources.fetch_targets, "Entreprises ciblées") if config.FETCH_TARGETS else []

    # 1) Notation de chaque offre (titre + texte) ; on écarte le hors-cible
    fetched, dropped, seen_ids = [], 0, set()
    for o in (ft or []) + (wt or []) + (tg or []):
        if o["id"] in seen_ids:
            continue
        seen_ids.add(o["id"])
        if scoring.excluded(o["title"], o.get("text", ""), o.get("contract", "")):
            dropped += 1
            continue
        s = scoring.score(o["title"], o.get("text", ""), o.get("experience", ""))
        o["target"] = targets.match(o["company"])
        bonus = config.TARGET_BONUS if o["target"] else 0
        if s["score"] + bonus < config.MIN_STORE_SCORE:
            dropped += 1
            continue
        o.update(rule_score=min(100, s["score"] + bonus), keywords=s["keywords"], years=s["years"])
        fetched.append(o)

    # 2) Lecture par Claude (si clé API) des offres prometteuses pas encore relues
    todo = [
        o for o in fetched
        if o["rule_score"] >= 45 and not (store.get(o["id"]) or {}).get("ai") and o.get("text")
    ]
    todo.sort(key=lambda o: o["rule_score"], reverse=True)
    reviews = llm.review(todo)

    # 3) Fusion avec l'archive
    new = []
    for o in fetched:
        old = store.get(o["id"])
        rv = reviews.get(o["id"]) or ({"ai": old.get("ai"), "note": old.get("note")} if old and old.get("ai") else None)
        o["score"] = round(0.4 * o["rule_score"] + 0.6 * rv["ai"]) if rv else o["rule_score"]
        o["ai"], o["note"] = (rv["ai"], rv["note"]) if rv else (None, "")
        o.pop("text", None)
        o.pop("experience", None)
        is_new = old is None
        o["first_seen"] = old["first_seen"] if old else today
        o["last_seen"] = today
        store[o["id"]] = o
        if is_new:
            new.append(o)

    # Anciennes entrées jamais notées : on les retire ; archive : retrait après KEEP_DAYS sans être revue
    limit = (datetime.now() - timedelta(days=config.KEEP_DAYS)).date().isoformat()
    store = {k: v for k, v in store.items() if "score" in v and v["last_seen"] >= limit}

    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(store, ensure_ascii=False, indent=0), encoding="utf-8")
    PAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
    PAGE_FILE.write_text(page.build(list(store.values()), today, config.NEW_DAYS), encoding="utf-8")

    pertinent = [o for o in new if o["score"] >= config.MIN_MAIL_SCORE]
    (PAGE_FILE.parent / "entreprises.html").write_text(carrieres_page.build_html(today), encoding="utf-8")

    print(
        f"Offres en archive : {len(store)} | écartées (hors cible) : {dropped} | nouvelles : {len(new)} "
        f"(pertinentes : {len(pertinent)}) | relues par Claude : {len(reviews)} | première synchro : {first_run}"
    )
    failed = [n for n, r in (("France Travail", ft), ("WTTJ", wt), ("Entreprises ciblées", tg)) if r is None]
    if failed:
        print(f"Sources en échec : {failed}", file=sys.stderr)

    to_mail = sorted(store.values(), key=lambda o: o["score"], reverse=True)[:25] if first_run else pertinent
    if to_mail and not args.no_mail:
        if "GMAIL_APP_PASSWORD" in os.environ and "MAIL_TO" in os.environ:
            others = 0 if first_run else len(new) - len(pertinent)
            send(build_mail(to_mail, len(store), first_run, others))
            print("Mail envoyé.")
        else:
            print("Mail non envoyé : GMAIL_APP_PASSWORD / MAIL_TO absents.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
