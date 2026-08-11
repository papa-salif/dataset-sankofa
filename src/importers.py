import csv
import io
import json
from typing import List, Optional


def parse_uploaded_file(filename: str, raw_bytes: bytes) -> List[dict]:
    """Parse un fichier .csv / .json / .txt en liste de dicts
    {text_fr, category, note, source}. Ne touche à aucune donnée existante,
    se contente d'extraire les lignes à importer."""
    text = raw_bytes.decode("utf-8-sig")
    ext = filename.rsplit(".", 1)[-1].lower()

    if ext == "csv":
        return _parse_csv(text)
    if ext == "json":
        return _parse_json(text)
    if ext == "txt":
        return _parse_txt(text)
    raise ValueError(f"Format non supporté : .{ext} (attendu : .csv, .json ou .txt)")


def _clean(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def _parse_csv(text: str) -> List[dict]:
    rows = []
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        text_fr = _clean(row.get("text_fr"))
        if not text_fr:
            continue
        rows.append(
            {
                "text_fr": text_fr,
                "category": _clean(row.get("category")),
                "note": _clean(row.get("note")),
                "source": _clean(row.get("source")),
            }
        )
    return rows


def _parse_json(text: str) -> List[dict]:
    rows = []
    data = json.loads(text)
    for item in data:
        if isinstance(item, str):
            text_fr = _clean(item)
            if text_fr:
                rows.append({"text_fr": text_fr, "category": None, "note": None, "source": None})
        elif isinstance(item, dict):
            text_fr = _clean(item.get("text_fr"))
            if text_fr:
                rows.append(
                    {
                        "text_fr": text_fr,
                        "category": _clean(item.get("category")),
                        "note": _clean(item.get("note")),
                        "source": _clean(item.get("source")),
                    }
                )
    return rows


def _parse_txt(text: str) -> List[dict]:
    rows = []
    for line in text.splitlines():
        text_fr = _clean(line)
        if text_fr:
            rows.append({"text_fr": text_fr, "category": None, "note": None, "source": None})
    return rows
