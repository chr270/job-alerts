# job-alerts

Veille quotidienne des offres d'emploi (France Travail + Welcome to the Jungle).

Chaque matin, GitHub Actions lance `run.py`, qui :
1. récupère les offres (config dans `config.py`),
2. détecte les nouvelles par rapport à `data/offers.json`,
3. régénère la page `docs/<PAGE_DIR>/index.html` (GitHub Pages),
4. envoie un mail des nouveautés via Gmail.

Secrets GitHub requis : `FT_CLIENT_ID`, `FT_CLIENT_SECRET`, `GMAIL_APP_PASSWORD`, `MAIL_TO`.

Test local : copier les identifiants dans `.env`, puis `python run.py --no-mail`.
