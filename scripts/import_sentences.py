"""Importe des phrases françaises depuis un CSV (colonne `text_fr`, `source` optionnelle)."""
import argparse
import csv
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.db import SessionLocal
from src.models import Sentence


def import_sentences(csv_path: str, source: Optional[str]):
    db = SessionLocal()
    count = 0
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            text_fr = (row.get("text_fr") or "").strip()
            if not text_fr:
                continue
            db.add(Sentence(text_fr=text_fr, source=source or row.get("source")))
            count += 1
    db.commit()
    db.close()
    print(f"{count} phrases importées depuis {csv_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path")
    parser.add_argument("--source", default=None)
    args = parser.parse_args()
    import_sentences(args.csv_path, args.source)
