"""Page "Pages carrières des entreprises" (entreprises.html) + export Markdown.

Lit careers.py (groupes) et data/careers_resolved.json (liens contrôlés par check_careers.py).
"""
import html
import json
import re
from pathlib import Path
from urllib.parse import quote_plus

import careers

ROOT = Path(__file__).parent


def short(name: str) -> str:
    """Nom utilisable comme mot de recherche : 'Covéa (MMA, MAAF, GMF)' -> 'Covéa'."""
    n = re.split(r" \(| / ", name)[0]
    return n.replace(" France", "").strip()


def search_links(name: str) -> list[tuple[str, str]]:
    q = quote_plus(short(name))
    idf = "%C3%8Ele-de-France"
    return [
        ("France Travail", f"https://candidat.francetravail.fr/offres/recherche?motsCles={q}&lieux=11R&offresPartenaires=true&tri=1"),
        ("WTTJ", f"https://www.welcometothejungle.com/fr/jobs?query={q}"),
        ("LinkedIn", f"https://www.linkedin.com/jobs/search/?keywords={q}%20marketing&location={idf}"),
        ("Indeed", f"https://fr.indeed.com/jobs?q={q}+marketing&l={idf}"),
        ("Google", f"https://www.google.com/search?q={q}+recrutement+marketing+CRM+offres+emploi"),
    ]


def load_resolved() -> dict:
    p = ROOT / "data" / "careers_resolved.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def build_html(updated: str) -> str:
    res = load_resolved()
    sections = []
    for group, items in careers.GROUPS.items():
        rows = []
        for name, _ in items:
            r = res.get(name, {})
            url = r.get("url", "")
            if url:
                label = "Page carrières" if r.get("primary") else "Site de l'entreprise"
                main = f'<a class="main" href="{html.escape(url)}" target="_blank" rel="noopener">{label} ↗</a>'
                if r.get("blocked"):
                    main += ' <span class="warn" title="Le site bloque les robots : le lien n\'a pas pu être contrôlé en détail">⚠</span>'
            else:
                main = '<span class="none">pas de page carrières fiable</span>'
            links = " ".join(
                f'<a class="chip" href="{html.escape(u)}" target="_blank" rel="noopener">{l}</a>'
                for l, u in search_links(name)
            )
            rows.append(f'<li><div class="n">{html.escape(name)}</div><div>{main}</div><div class="ch">{links}</div></li>')
        sections.append(f"<h2>{html.escape(group)} <span class=\"c\">{len(items)}</span></h2><ul>{''.join(rows)}</ul>")
    return TEMPLATE.replace("__SECTIONS__", "".join(sections)).replace("__UPDATED__", updated)


def build_markdown() -> str:
    res = load_resolved()
    out = [
        "# Pages carrières des entreprises ciblées",
        "",
        "Source de la liste : CV_Christopher_EDOUARD_grandes_entreprises_salaires.md. "
        "« Page carrières » = lien contrôlé ; « Site » = accueil de l'entreprise (page carrières introuvable).",
        "",
    ]
    for group, items in careers.GROUPS.items():
        out += [f"## {group}", ""]
        for name, _ in items:
            r = res.get(name, {})
            url = r.get("url", "")
            kind = "Page carrières" if r.get("primary") else "Site"
            lines = f"- **{name}** : " + (f"[{kind}]({url})" if url else "pas de page carrières fiable")
            alt = " · ".join(f"[{l}]({u})" for l, u in search_links(name))
            out.append(f"{lines}  \n  Recherche : {alt}")
        out.append("")
    return "\n".join(out)


TEMPLATE = """<!DOCTYPE html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow"><title>Pages carrières</title>
<style>
  :root { --bg:#f6f7f9; --card:#fff; --txt:#1c2330; --mut:#667085; --acc:#1d4ed8; --bd:#e4e7ec; }
  @media (prefers-color-scheme: dark) { :root { --bg:#10141b; --card:#171c26; --txt:#e6e9ef; --mut:#98a2b3; --acc:#7aa2ff; --bd:#262d3a; } }
  * { box-sizing:border-box; }
  body { margin:0; font:14px/1.4 system-ui,-apple-system,Segoe UI,sans-serif; background:var(--bg); color:var(--txt); }
  header { position:sticky; top:0; background:var(--bg); padding:10px 14px; border-bottom:1px solid var(--bd); z-index:2; }
  h1 { font-size:18px; margin:0 0 6px; } h2 { font-size:15px; margin:18px 0 6px; } .c { color:var(--mut); font-weight:400; }
  a { color:var(--acc); text-decoration:none; } a:hover { text-decoration:underline; }
  input { padding:7px 9px; border:1px solid var(--bd); border-radius:8px; background:var(--card); color:var(--txt); font-size:14px; width:100%; max-width:380px; }
  main { padding:0 14px 40px; max-width:900px; margin:0 auto; }
  ul { list-style:none; padding:0; margin:0; }
  li { background:var(--card); border:1px solid var(--bd); border-radius:10px; padding:9px 12px; margin-bottom:7px; }
  .n { font-weight:600; } .main { font-weight:600; } .none, .sub { color:var(--mut); font-size:12px; } .warn { color:#d97706; }
  .ch { margin-top:5px; } .chip { display:inline-block; font-size:12px; padding:1px 8px; border:1px solid var(--bd); border-radius:99px; margin:2px 3px 0 0; }
</style></head><body>
<header><h1>Pages carrières des entreprises ciblées</h1>
<input type="search" id="q" placeholder="Filtrer une entreprise…">
<div class="sub" style="margin-top:5px"><a href="./">← Retour aux offres</a> · liens contrôlés le __UPDATED__ · les recherches s'ouvrent sur le site choisi</div></header>
<main>__SECTIONS__</main>
<script>
document.getElementById("q").addEventListener("input", e => {
  const q = e.target.value.toLowerCase();
  document.querySelectorAll("li").forEach(li => li.hidden = q && !li.querySelector(".n").textContent.toLowerCase().includes(q));
});
</script></body></html>
"""
