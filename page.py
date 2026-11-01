"""Génère la page web unique (HTML statique, lisible sur téléphone) à partir de template.html."""
import json
from pathlib import Path

TEMPLATE = (Path(__file__).parent / "template.html").read_text(encoding="utf-8")
FIELDS = [
    "id", "source", "title", "company", "location", "contract", "salary", "remote", "published",
    "url", "snippet", "first_seen", "last_seen", "score", "note", "keywords",
]


def build(offers: list[dict], today: str, new_days: int) -> str:
    slim = [{k: o.get(k) for k in FIELDS} for o in offers]
    data = json.dumps(slim, ensure_ascii=False).replace("</", "<\\/")
    return (
        TEMPLATE.replace("__DATA__", data)
        .replace("__NEWDAYS__", str(new_days))
        .replace("__TODAY__", today)
        .replace("__UPDATED__", today)
    )
