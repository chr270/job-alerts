"""Réglages de la veille quotidienne. Modifiez les listes ci-dessous puis poussez sur GitHub."""

# Requêtes envoyées à France Travail (API : tous les mots doivent figurer dans l'offre)
FT_QUERIES = [
    "marketing automation",
    "CRM",
    "Salesforce",
    "marketing digital",
    "chef de projet CRM",
    "traffic manager",
    "growth marketing",
    "MarTech",
    "acquisition digitale",
    "SFMC",
]
FT_REGION = "11"  # 11 = Île-de-France
FT_MAX_PER_QUERY = 450
FT_DAYS = 31  # offres publiées depuis N jours (1, 3, 7, 14 ou 31)

# Requêtes envoyées à Welcome to the Jungle
WTTJ_QUERIES = [
    "CRM",
    "Salesforce",
    "marketing automation",
    "marketing digital",
    "MarTech",
    "data marketing",
    "growth marketing",
]
WTTJ_STATE = "Ile-de-France"  # on garde cette région + le télétravail complet
WTTJ_MAX_PAGES = 4

# Une offre disparaît de la page si elle n'a pas été revue depuis N jours
KEEP_DAYS = 10
# Une offre garde le badge "Nouveau" pendant N jours
NEW_DAYS = 2

# Dossier de la page web (nom secret : toute personne ayant le lien peut la voir)
PAGE_DIR = "a93b427552cd8f37"
PAGE_URL = f"https://chr270.github.io/job-alerts/{PAGE_DIR}/"
