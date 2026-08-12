"""Ajoute un code contributeur unique (identité réelle, indépendante du nom
affiché) et génère un code pour les contributeurs déjà existants. Retire
l'ancienne contrainte d'unicité sur `name` (deux personnes peuvent avoir
choisi le même nom d'affichage)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text

from src.db import SessionLocal, engine
from src.models import Contributor
from src.repository import generate_unique_contributor_code


def main():
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE contributors ADD COLUMN IF NOT EXISTS code VARCHAR(20)"))

    db = SessionLocal()
    missing = db.query(Contributor).filter(Contributor.code.is_(None)).all()
    for contributor in missing:
        contributor.code = generate_unique_contributor_code(db)
        print(f"{contributor.name} -> {contributor.code}")
    db.commit()
    db.close()

    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE contributors ALTER COLUMN code SET NOT NULL"))
        conn.execute(
            text(
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint WHERE conname = 'contributors_code_key'
                    ) THEN
                        ALTER TABLE contributors ADD CONSTRAINT contributors_code_key UNIQUE (code);
                    END IF;
                END $$;
                """
            )
        )
        conn.execute(
            text(
                """
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1 FROM pg_constraint WHERE conname = 'contributors_name_key'
                    ) THEN
                        ALTER TABLE contributors DROP CONSTRAINT contributors_name_key;
                    END IF;
                END $$;
                """
            )
        )
    print("Migration terminée.")


if __name__ == "__main__":
    main()
