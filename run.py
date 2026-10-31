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

import config
import page
import sources

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


def build_mail(new: list[dict], total: int, first_run: bool) -> EmailMessage:
    new = sorted(new, key=lambda o: o.get("published", ""), reverse=True)
    shown = new[:60]
    title = (
        f"Veille emploi : {total} offres suivies (première synchronisation)"
        if first_run
        else f"{len(new)} nouvelle{'s' if len(new) > 1 else ''} offre{'s' if len(new) > 1 else ''} d'emploi"
    )
    rows, text = [], [title, "", f"Toutes les offres : {config.PAGE_URL}", ""]
    for o in shown:
        meta = " · ".join(x for x in [o["company"], o["location"], o["contract"], o["source"]] if x)
        rows.append(
            f'<li style="margin-bottom:10px"><a href="{html.escape(o["url"])}"><b>{html.escape(o["title"])}</b></a>'
            f'<br><span style="color:#667085">{html.escape(meta)}</span></li>'
        )
        text.append(f"- {o['title']} | {meta}\n  {o['url']}")
    more = f"<p>… et {len(new) - len(shown)} autres sur la page.</p>" if len(new) > len(shown) else ""
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

    fetched = (ft or []) + (wt or [])
    new = []
    for o in fetched:
        old = store.get(o["id"])
        if old:
            old.update({**o, "first_seen": old["first_seen"]})
            old["last_seen"] = today
        else:
            o["first_seen"] = o["last_seen"] = today
            store[o["id"]] = o
            new.append(o)

    # Retire les offres qu'on ne voit plus depuis KEEP_DAYS jours
    limit = (datetime.now() - timedelta(days=config.KEEP_DAYS)).date().isoformat()
    store = {k: v for k, v in store.items() if v["last_seen"] >= limit}

    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(store, ensure_ascii=False, indent=0), encoding="utf-8")
    PAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
    PAGE_FILE.write_text(page.build(list(store.values()), today, config.NEW_DAYS), encoding="utf-8")

    print(f"Offres suivies : {len(store)} | nouvelles : {len(new)} | première synchro : {first_run}")
    failed = [n for n, r in (("France Travail", ft), ("WTTJ", wt)) if r is None]
    if failed:
        print(f"Sources en échec : {failed}", file=sys.stderr)

    to_mail = list(store.values()) if first_run else new
    if to_mail and not args.no_mail:
        if "GMAIL_APP_PASSWORD" in os.environ and "MAIL_TO" in os.environ:
            if first_run:  # première synchro : on n'envoie que les plus récentes
                to_mail = sorted(to_mail, key=lambda o: o.get("published", ""), reverse=True)[:25]
            send(build_mail(to_mail, len(store), first_run))
            print("Mail envoyé.")
        else:
            print("Mail non envoyé : GMAIL_APP_PASSWORD / MAIL_TO absents.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
