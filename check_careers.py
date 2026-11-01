#!/usr/bin/env python3
"""Contrôle les liens de careers.py. Écrit data/careers_check.json : {url: {"status": int|None, "final": url, "ok": bool}}.

ok = la page existe (200-399) ou répond mais bloque les robots (401/403/429/999).
"""
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

import careers

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
BLOCKED = {400, 401, 403, 429, 502, 503, 999}


def check(url: str) -> tuple[str, dict]:
    try:
        with httpx.Client(follow_redirects=True, timeout=20, headers={"User-Agent": UA, "Accept-Language": "fr-FR,fr;q=0.9"}) as c:
            r = c.get(url)
        ok = r.status_code < 400 or r.status_code in BLOCKED
        return url, {"status": r.status_code, "final": str(r.url), "ok": ok}
    except Exception as e:  # DNS, TLS, délai dépassé...
        return url, {"status": None, "final": "", "ok": False, "error": type(e).__name__}


def resolve() -> dict:
    """Pour chaque entreprise : première adresse valide (principale, puis secours). Vide si aucune."""
    cands: dict[str, list[str]] = {}
    for g in careers.GROUPS.values():
        for name, url in g:
            cands[name] = ([url] if url else []) + careers.ALT.get(name, [])
    urls = sorted({u for c in cands.values() for u in c})
    with ThreadPoolExecutor(8) as ex:
        res = dict(ex.map(check, urls))
    out = {}
    for name, lst in cands.items():
        ok = next((u for u in lst if res[u]["ok"]), "")
        out[name] = {"url": ok, "primary": bool(lst) and ok == lst[0], "blocked": bool(ok) and res[ok]["status"] in BLOCKED}
    return out


if __name__ == "__main__":
    out = resolve()
    p = Path(__file__).parent / "data" / "careers_resolved.json"
    p.parent.mkdir(exist_ok=True)
    p.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    ok = [n for n, v in out.items() if v["url"]]
    print(f"{len(ok)}/{len(out)} entreprises avec un lien valide ; page carrières directe : {sum(v['primary'] for v in out.values())}")
    print("Sans lien :", [n for n, v in out.items() if not v["url"]])
    print("Accueil/secours :", [n for n, v in out.items() if v["url"] and not v["primary"]])
