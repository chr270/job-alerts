"""Génère la page web unique (HTML statique, lisible sur téléphone)."""
import json

TEMPLATE = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>Offres d'emploi</title>
<style>
  :root { --bg:#f6f7f9; --card:#fff; --txt:#1c2330; --mut:#667085; --acc:#1d4ed8; --new:#16a34a; --bd:#e4e7ec; }
  @media (prefers-color-scheme: dark) {
    :root { --bg:#10141b; --card:#171c26; --txt:#e6e9ef; --mut:#98a2b3; --acc:#7aa2ff; --new:#4ade80; --bd:#262d3a; }
  }
  * { box-sizing:border-box; }
  body { margin:0; font:15px/1.45 system-ui,-apple-system,Segoe UI,sans-serif; background:var(--bg); color:var(--txt); }
  header { position:sticky; top:0; background:var(--bg); padding:12px 14px; border-bottom:1px solid var(--bd); z-index:2; }
  h1 { font-size:18px; margin:0 0 8px; }
  .sub { color:var(--mut); font-size:13px; font-weight:400; }
  .bar { display:flex; flex-wrap:wrap; gap:8px; }
  input,select { padding:8px 10px; border:1px solid var(--bd); border-radius:8px; background:var(--card); color:var(--txt); font-size:15px; }
  input[type=search] { flex:1 1 200px; }
  label { display:flex; align-items:center; gap:6px; font-size:14px; }
  main { padding:12px 14px 40px; max-width:900px; margin:0 auto; }
  .card { background:var(--card); border:1px solid var(--bd); border-radius:12px; padding:12px 14px; margin-bottom:10px; }
  .card a.t { color:var(--acc); font-weight:600; text-decoration:none; font-size:16px; }
  .card a.t:hover { text-decoration:underline; }
  .meta { color:var(--mut); font-size:13px; margin-top:4px; }
  .tag { display:inline-block; font-size:12px; padding:1px 8px; border-radius:99px; border:1px solid var(--bd); margin-right:4px; }
  .new { color:var(--new); border-color:var(--new); font-weight:600; }
  .snip { margin-top:6px; font-size:13px; color:var(--mut); }
  .empty { text-align:center; color:var(--mut); padding:40px 0; }
</style>
</head>
<body>
<header>
  <h1>Offres d'emploi <span class="sub" id="count"></span></h1>
  <div class="bar">
    <input type="search" id="q" placeholder="Rechercher (titre, entreprise, ville)…">
    <select id="src"><option value="">Toutes sources</option></select>
    <select id="ctr"><option value="">Tous contrats</option></select>
    <select id="sort"><option value="pub">Plus récentes</option><option value="seen">Dernières apparues</option></select>
    <label><input type="checkbox" id="onlynew"> Nouveautés</label>
  </div>
  <div class="sub" style="margin-top:6px">Mis à jour le __UPDATED__</div>
</header>
<main id="list"></main>
<script>
const OFFERS = __DATA__;
const NEW_DAYS = __NEWDAYS__;
const $ = id => document.getElementById(id);
const today = new Date("__TODAY__T00:00:00");
const isNew = o => (today - new Date(o.first_seen + "T00:00:00")) / 864e5 < NEW_DAYS;

function fill(sel, key) {
  [...new Set(OFFERS.map(o => o[key]).filter(Boolean))].sort().forEach(v => {
    const op = document.createElement("option"); op.value = v; op.textContent = v; $(sel).appendChild(op);
  });
}
fill("src", "source"); fill("ctr", "contract");

function render() {
  const q = $("q").value.toLowerCase().trim();
  let rows = OFFERS.filter(o =>
    (!q || (o.title + " " + o.company + " " + o.location + " " + o.snippet).toLowerCase().includes(q)) &&
    (!$("src").value || o.source === $("src").value) &&
    (!$("ctr").value || o.contract === $("ctr").value) &&
    (!$("onlynew").checked || isNew(o)));
  const k = $("sort").value === "seen" ? "first_seen" : "published";
  rows.sort((a, b) => (b[k] || "").localeCompare(a[k] || "") || (b.first_seen || "").localeCompare(a.first_seen || ""));
  $("count").textContent = "· " + rows.length + " / " + OFFERS.length;
  const list = $("list"); list.textContent = "";
  if (!rows.length) { const d = document.createElement("div"); d.className = "empty"; d.textContent = "Aucune offre."; list.appendChild(d); return; }
  rows.slice(0, 400).forEach(o => {
    const c = document.createElement("div"); c.className = "card";
    const a = document.createElement("a"); a.className = "t"; a.href = o.url; a.target = "_blank"; a.rel = "noopener"; a.textContent = o.title;
    const m = document.createElement("div"); m.className = "meta";
    const parts = [o.company, o.location, o.contract, o.remote, o.salary].filter(Boolean).join(" · ");
    m.textContent = parts + (o.published ? " · publiée le " + o.published : "");
    const tags = document.createElement("div"); tags.className = "meta";
    if (isNew(o)) { const t = document.createElement("span"); t.className = "tag new"; t.textContent = "Nouveau"; tags.appendChild(t); }
    const s = document.createElement("span"); s.className = "tag"; s.textContent = o.source; tags.appendChild(s);
    c.append(a, m, tags);
    if (o.snippet) { const sn = document.createElement("div"); sn.className = "snip"; sn.textContent = o.snippet.slice(0, 200) + "…"; c.appendChild(sn); }
    list.appendChild(c);
  });
}
["q","src","ctr","sort","onlynew"].forEach(id => $(id).addEventListener("input", render));
render();
</script>
</body>
</html>
"""


def build(offers: list[dict], today: str, new_days: int) -> str:
    data = json.dumps(offers, ensure_ascii=False).replace("</", "<\\/")
    return (
        TEMPLATE.replace("__DATA__", data)
        .replace("__NEWDAYS__", str(new_days))
        .replace("__TODAY__", today)
        .replace("__UPDATED__", today)
    )
