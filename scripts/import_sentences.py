"""Importe des phrases françaises depuis un fichier .csv/.json/.txt
(même logique de parsing que l'onglet « Import en masse » de la console admin)."""
import argparse
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import repository
from src.db import SessionLocal
from src.importers import parse_uploaded_file


def import_sentences(file_path: str, source: Optional[str]):
    path = Path(file_path)
    rows = parse_uploaded_file(path.name, path.read_bytes())

    db = SessionLocal()
    count = repository.bulk_create_sentences(db, rows, default_source=source)
    db.close()
    print(f"{count} phrases importées depuis {file_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("file_path", help="Fichier .csv, .json ou .txt")
    parser.add_argument("--source", default=None)
    args = parser.parse_args()
    import_sentences(args.file_path, args.source)
