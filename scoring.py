"""Note de pertinence (0-100) d'une offre par rapport au profil de Christopher.

Lit le titre ET le texte de l'offre. Règles basées sur le CV (voir PROFIL ci-dessous).
Modifiez les listes pour ajuster le tri.
"""
import re

# Titres écartés d'office (hors cible) : l'offre n'est même pas conservée
EXCLUDE_TITLE = re.compile(
    r"d[ée]veloppeu|developer|ing[ée]nieur|architecte|data engineer|data scientist|devops|"
    r"comptab|commercial|business developer|account executive|\bsdr\b|\bbdr\b|"
    r"\bstage\b|stagiaire|apprenti|directeur|directrice|\bhead of\b|\bvp\b|\bchief\b|"
    r"\bcto\b|\bcmo\b|juridique|\bpaie\b|infirmi|chauffeur|vendeu|conseiller de vente|recrut|"
    r"graphiste|vid[ée]aste|photograph|r[ée]dacteur|journaliste|community manager",
    re.I,
)

# Intitulés cœur de cible (+points). Chaque motif ne compte qu'une fois : on prend le meilleur.
TITLE_POINTS = [
    (r"marketing automation|automatisation marketing|sfmc|marketing cloud|eloqua|journey builder", 55),
    (r"\bcrm\b|lifecycle|cycle de vie|fid[ée]lisation|campagnes? (?:e-?mail|marketing|crm)|emailing", 50),
    (r"martech|marketing ops|revops|marketing op[ée]rationnel", 50),
    (r"traffic manager|acquisition|m[ée]dia trafficker|trafficker|growth|\bsea\b|\bseo\b|r[ée]f[ée]rencement|search marketing|paid", 48),
    (r"marketing digital|digital marketing|webmarketing|web marketing|e-?commerce|communication digitale", 44),
    (r"chef(?:fe)? de projet.*(?:digital|marketing|web)|digital project|chef(?:fe)? de projets? (?:digitaux|web)", 42),
    (r"data marketing|reporting marketing|analytics|web analyst|marketing analyst|chargé.* d'?analyse", 40),
    (r"no-?code|automatisation|\bia\b|intelligence artificielle|ai enablement", 32),
    (r"marketing|salesforce|digital", 28),
]

# Séniorité (le CV vise "chargé de / junior à confirmé", ~4 ans d'expérience)
SENIORITY = [
    (r"\bjunior\b|d[ée]butant|chargé|charge de|assistant|\bspécialiste\b|specialiste", +8),
    (r"\bsenior\b|\bsénior\b|confirm[ée]|exp[ée]riment[ée]", -22),
    (r"\blead\b|\bprincipal\b|\bexpert\b", -18),
    (r"responsable|\bmanager\b|\bmanageur", -10),
    (r"freelance|ind[ée]pendant|portage", -20),
]

# Mots-clés du CV recherchés dans le texte de l'offre (+points, plafonnés)
KEYWORDS = {
    "SFMC / Marketing Cloud": (r"sfmc|marketing cloud|journey builder|exact ?target", 7),
    "Eloqua": (r"eloqua", 7),
    "Salesforce": (r"salesforce", 4),
    "Marketing automation": (r"marketing automation|automatisation marketing|automation", 5),
    "CRM": (r"\bcrm\b", 3),
    "Emailing": (r"e-?mailing|newsletter|campagnes? e-?mail|email marketing", 3),
    "Segmentation / scénarios": (r"segmentation|sc[ée]nario|workflow|parcours client|lifecycle", 3),
    "SEO": (r"\bseo\b|r[ée]f[ée]rencement naturel|netlinking", 3),
    "SEA / Ads": (r"\bsea\b|google ads|meta ads|facebook ads|social ads|paid media|retargeting", 3),
    "Analytics": (r"google analytics|\bga4\b|tag manager|\bgtm\b|looker|power ?bi|piano analytics", 3),
    "Reporting / KPI": (r"reporting|\bkpi\b|tableaux? de bord", 2),
    "No-code / automatisation": (r"n8n|zapier|\bmake\b|no-?code|webflow|airtable", 3),
    "Gestion de projet": (r"\bjira\b|monday|clickup|gestion de projet|pilotage de projet", 2),
    "RGPD": (r"rgpd|cnil|gdpr", 2),
    "IA": (r"\bia\b|intelligence artificielle|chatgpt|copilot|agents? ia", 2),
    "E-commerce": (r"e-?commerce|shopify", 2),
}
KEYWORD_CAP = 30

# Signaux négatifs dans le texte (poste trop technique, trop commercial...)
TEXT_NEGATIVE = [
    (r"prospection|chiffre d'affaires à atteindre|objectifs? commerciaux|d[ée]marchage|vente en direct", -10),
    (r"python|java\b|javascript|\bsql\b avanc|apex|développement de composants", -8),
]

EXP_RE = re.compile(r"(\d{1,2})\s*(?:\+\s*)?(?:ans?|années?)\b", re.I)


def required_years(text: str, experience_label: str = "") -> int | None:
    """Années d'expérience demandées (la plus basse trouvée), ou None."""
    label = (experience_label or "").lower()
    if "débutant" in label or "debutant" in label:
        return 0
    found = [int(m.group(1)) for m in EXP_RE.finditer(label)]
    if not found:
        found = [int(m.group(1)) for m in EXP_RE.finditer(text) if int(m.group(1)) <= 15]
    return min(found) if found else None


# Alternance / stage / apprentissage : hors cible (profil à ~4 ans d'expérience, CDI/CDD recherché)
EXCLUDE_CONTRACT = re.compile(
    r"alternan|apprenti|professionnalisation|\bstage\b|stagiaire|internship|work-?study", re.I
)


def excluded(title: str, text: str = "", contract: str = "") -> bool:
    return bool(
        EXCLUDE_TITLE.search(title)
        or EXCLUDE_CONTRACT.search(title + " " + contract + " " + text[:600])
    )


def score(title: str, text: str, experience_label: str = "") -> dict:
    t = title.lower()
    body = (title + " " + text).lower()

    base = max((pts for pat, pts in TITLE_POINTS if re.search(pat, t)), default=10)
    adj = sum(pts for pat, pts in SENIORITY if re.search(pat, t))

    matched, kw_pts = [], 0
    for name, (pat, pts) in KEYWORDS.items():
        if re.search(pat, body):
            matched.append(name)
            kw_pts += pts
    kw_pts = min(kw_pts, KEYWORD_CAP)

    neg = sum(pts for pat, pts in TEXT_NEGATIVE if re.search(pat, body))

    years = required_years(text, experience_label)
    exp = 0
    if years is not None:
        exp = {0: 8, 1: 8, 2: 6, 3: 4, 4: 0, 5: -12}.get(years, -30 if years >= 6 else 0)

    total = max(0, min(100, base + adj + kw_pts + neg + exp))
    return {"score": total, "keywords": matched, "years": years}


def label(s: int) -> str:
    return "Très pertinent" if s >= 70 else "Pertinent" if s >= 50 else "Moyen" if s >= 35 else "Faible"
