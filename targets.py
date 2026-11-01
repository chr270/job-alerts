"""Entreprises ciblées (liste du fichier CV_..._grandes_entreprises_salaires.md).

NAMES : nom affiché, utilisé aussi comme mot de recherche.
ALIASES : motif de reconnaissance du nom d'entreprise quand le nom seul est ambigu.
"""
import re
import unicodedata

NAMES = [
    # CAC 40
    "Accor", "Air Liquide", "Airbus", "ArcelorMittal", "Axa", "BNP Paribas", "Bouygues", "Capgemini",
    "Carrefour", "Crédit Agricole", "Danone", "Dassault Systèmes", "Eiffage", "Engie", "EssilorLuxottica",
    "Eurofins", "Hermès", "Kering", "Legrand", "L'Oréal", "LVMH", "Michelin", "Orange", "Pernod Ricard",
    "Publicis", "Renault", "Safran", "Saint-Gobain", "Sanofi", "Schneider Electric", "Société Générale",
    "Stellantis", "STMicroelectronics", "Teleperformance", "Thales", "TotalEnergies",
    "Unibail-Rodamco-Westfield", "Veolia", "Vinci",
    # Banque / assurance / leasing / mobilité
    "BPCE", "Natixis", "Crédit Mutuel", "MAIF", "MACIF", "Generali", "Covéa", "MMA", "MAAF", "GMF",
    "Allianz", "Arval", "Alphabet Mobility", "Free2Move",
    # Retail / luxe / e-commerce
    "Printemps", "Galeries Lafayette", "Fnac Darty", "Auchan", "Leclerc", "Cdiscount", "Decathlon",
    "Adeo", "Leroy Merlin", "Kiabi", "Sephora", "Nocibé", "Yves Rocher", "Etam",
    # Tech / MarTech / SaaS
    "Salesforce", "Adobe", "HubSpot", "Criteo", "Contentsquare", "Doctolib", "BlaBlaCar", "Deezer",
    "Younited", "Qonto", "Back Market", "Meta", "Google", "Amazon", "Microsoft", "Apple", "LinkedIn",
    "TikTok", "Booking.com",
    # Conseil / agences
    "Havas", "WPP", "Ogilvy", "GroupM", "Accenture", "Wavestone", "Sopra Steria", "Eviden", "Atos",
    "Publicis Sapient", "Dentsu", "Klépierre",
    # Télécoms / médias
    "Bouygues Telecom", "SFR", "Iliad", "Canal+", "TF1", "M6", "France Télévisions",
    # Biens de consommation
    "Nestlé", "Unilever", "Procter & Gamble", "PepsiCo", "Coca-Cola", "Ferrero",
    # Marques automobiles (Renault, Stellantis, Free2Move et Arval sont déjà plus haut)
    "Dacia", "Alpine", "Mobilize", "Peugeot", "Citroën", "DS Automobiles", "Opel", "Fiat", "Jeep",
    "Toyota", "Volkswagen Group", "BMW", "Mercedes-Benz", "Ford", "Hyundai", "Kia", "Nissan", "Mazda",
    "Volvo Cars", "Tesla", "Porsche", "Honda", "Mitsubishi Motors", "Suzuki", "MG Motor", "BYD",
    "Jaguar Land Rover",
    # Ajouts (avantages salariés, voir fichier grandes entreprises, section 5)
    "Dassault Aviation", "Malakoff Humanis", "Air France-KLM", "ArianeGroup",
]

ALIASES = {
    "Meta": r"\bmeta (platforms|france)\b|^meta$",
    "Google": r"\bgoogle\b",
    "Apple": r"^apple\b",
    "Orange": r"\borange\b",
    "Alphabet Mobility": r"alphabet (mobility|fleet)",
    "Iliad": r"\biliad\b|\bfree mobile\b|\bfree\b ?(sas|infrastructure)?$",
    "SFR": r"\bsfr\b|altice",
    "M6": r"\bm6\b|groupe m6",
    "Renault": r"\brenault\b|ampere",
    "Printemps": r"\bprintemps\b|place des tendances",
    "Publicis": r"\bpublicis\b|\bsapient\b|\bdigitas\b|\bleo burnett\b|\bsaatchi\b",
    "Adeo": r"\badeo\b|leroy merlin|bricoman",
    "Crédit Agricole": r"credit agricole|\bca\b ?(sa|cib|consumer|assurances)",
    "Procter & Gamble": r"procter|\bp&g\b",
    "Coca-Cola": r"coca cola",
    "Generali": r"\bgenerali\b",
    "Covéa": r"\bcovea\b|\bmma\b|\bmaaf\b|\bgmf\b",
    "MMA": r"\bmma\b",
    "Atos": r"\batos\b",
    "Alpine": r"alpine (cars|racing|renault)|^alpine$",
    "Mobilize": r"mobilize|rci bank",
    "Toyota": r"toyota|lexus",
    "Volkswagen Group": r"volkswagen|\bvw\b|\baudi\b|skoda|cupra|\bseat\b",
    "BMW": r"\bbmw\b|mini france|bmw group",
    "Mercedes-Benz": r"mercedes",
    "Ford": r"\bford\b",
    "Volvo Cars": r"volvo cars?|volvo car",
    "MG Motor": r"\bmg motor\b|saic motor",
    "Jaguar Land Rover": r"jaguar|land rover",
    "Mitsubishi Motors": r"mitsubishi motors",
    "Stellantis": r"stellantis|\bpsa\b|groupe psa|\bfca\b",
    "Air France-KLM": r"air france|\bklm\b",
    "Citroën": r"\bcitroen\b",
    "DS Automobiles": r"\bds automobiles\b",
}


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9&+]+", " ", s).strip()


_PATTERNS = {
    n: re.compile(ALIASES.get(n, r"\b" + re.escape(norm(n)) + r"\b"))
    for n in NAMES
}


def match(company: str) -> str:
    """Nom de l'entreprise ciblée correspondant, ou '' si aucune."""
    c = norm(company)
    if not c:
        return ""
    for name, pat in _PATTERNS.items():
        if pat.search(c):
            return name
    return ""
