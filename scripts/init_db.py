"""Crée les tables dans PostgreSQL à partir des modèles SQLAlchemy."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import models  # noqa: F401  (nécessaire pour enregistrer les modèles)
from src.db import Base, engine


def main():
    Base.metadata.create_all(bind=engine)
    print("Tables créées avec succès.")


if __name__ == "__main__":
    main()
