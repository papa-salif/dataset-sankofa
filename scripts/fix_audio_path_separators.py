"""Normalise les chemins audio déjà stockés en base : remplace les antislashs
(introduits par une exécution locale sous Windows) par des slashs, pour que
les fichiers restent trouvables aussi depuis les conteneurs Linux."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.db import SessionLocal
from src.models import Recording


def main():
    db = SessionLocal()
    fixed = 0
    for recording in db.query(Recording).all():
        changed = False
        if recording.original_path and "\\" in recording.original_path:
            recording.original_path = recording.original_path.replace("\\", "/")
            changed = True
        if recording.cleaned_path and "\\" in recording.cleaned_path:
            recording.cleaned_path = recording.cleaned_path.replace("\\", "/")
            changed = True
        if changed:
            fixed += 1
    db.commit()
    db.close()
    print(f"{fixed} enregistrement(s) corrigé(s).")


if __name__ == "__main__":
    main()
