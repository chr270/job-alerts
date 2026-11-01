"""Réglages de la veille quotidienne. Modifiez les listes ci-dessous puis poussez sur GitHub."""

# Requêtes envoyées à France Travail (API : tous les mots doivent figurer dans l'offre)
FT_QUERIES = [
    "marketing automation",
    "CRM",
    "Salesforce",
    "emailing",
    "marketing digital",
    "traffic manager",
    "acquisition digitale",
    "SEO",
    "growth marketing",
    "MarTech",
    "e-commerce",
    "chef de projet digital",
    "communication digitale",
    "Marketing Cloud",
    "Adobe Campaign",
    "Braze",
    "consultant CRM",
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
    "traffic manager",
    "acquisition digitale",
    "SEO",
    "emailing",
    "growth marketing",
    "Marketing Cloud",
    "Adobe Campaign",
    "Braze",
]
WTTJ_STATE = "Ile-de-France"  # on garde cette région + le télétravail complet
WTTJ_MAX_PAGES = 4

# Archive : une offre n'est plus affichée "en ligne" si elle n'est plus vue, mais reste dans le tableau
# (supprimée seulement après N jours sans être revue)
KEEP_DAYS = 180

# Seuils de pertinence (0-100)
MIN_STORE_SCORE = 30     # en dessous, l'offre n'est pas conservée du tout
MIN_MAIL_SCORE = 50      # seules les nouvelles offres au-dessus sont détaillées dans le mail
# Recherche entreprise par entreprise (liste dans targets.py) + bonus de note pour ces entreprises
FETCH_TARGETS = True
TARGET_BONUS = 10

# Une offre garde le badge "Nouveau" pendant N jours
NEW_DAYS = 2

# Dossier de la page web (nom secret : toute personne ayant le lien peut la voir)
PAGE_DIR = "a93b427552cd8f37"
PAGE_URL = f"https://chr270.github.io/job-alerts/{PAGE_DIR}/"
