"""Autorise translations.text_moore à être vide : un contributeur peut
désormais choisir de ne faire que l'audio (sans taper le texte mooré)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text

from src.db import engine


def main():
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE translations ALTER COLUMN text_moore DROP NOT NULL"))
    print("Migration terminée : text_moore est maintenant nullable.")


if __name__ == "__main__":
    main()
