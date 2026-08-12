"""Exporte le dataset : en .json (métadonnées seules) ou en .zip (manifest +
fichiers audio, prêt à être importé dans un pipeline d'entraînement)."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.db import SessionLocal
from src.export_utils import build_dataset_entries, build_dataset_zip


def export_dataset(output_path: str, only_validated: bool):
    db = SessionLocal()

    if output_path.lower().endswith(".zip"):
        zip_bytes, skipped = build_dataset_zip(db, only_validated=only_validated)
        db.close()
        with open(output_path, "wb") as f:
            f.write(zip_bytes)
        if skipped:
            print(f"{skipped} enregistrement(s) ignoré(s) : fichier audio introuvable sur disque.")
        print(f"Archive exportée dans {output_path}")
    else:
        entries = build_dataset_entries(db, only_validated=only_validated)
        db.close()
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(entries, f, ensure_ascii=False, indent=2)
        print(f"{len(entries)} entrées exportées dans {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output_path", help="Chemin de sortie : .json (métadonnées) ou .zip (avec audio)")
    parser.add_argument(
        "--all", dest="only_validated", action="store_false",
        help="Inclure aussi les enregistrements non validés",
    )
    parser.set_defaults(only_validated=True)
    args = parser.parse_args()
    export_dataset(args.output_path, args.only_validated)
