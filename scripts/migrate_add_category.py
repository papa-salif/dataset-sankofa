"""Migration idempotente : ajoute les colonnes category/note à la table sentences
sans toucher aux données existantes (utile quand les tables ont déjà été créées
par une version antérieure de init_db.py)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text

from src.db import engine


def main():
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE sentences ADD COLUMN IF NOT EXISTS category VARCHAR(50)"))
        conn.execute(text("ALTER TABLE sentences ADD COLUMN IF NOT EXISTS note TEXT"))
    print("Migration appliquée : colonnes category/note prêtes sur sentences.")


if __name__ == "__main__":
    main()
