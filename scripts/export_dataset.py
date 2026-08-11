"""Exporte le dataset (phrase FR, traduction mooré, chemins audio) en JSON."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.db import SessionLocal
from src.models import Recording, RecordingStatus, Sentence, Translation


def export_dataset(output_path: str, only_validated: bool):
    db = SessionLocal()
    query = (
        db.query(Recording, Translation, Sentence)
        .join(Translation, Recording.translation_id == Translation.id)
        .join(Sentence, Translation.sentence_id == Sentence.id)
    )
    if only_validated:
        query = query.filter(Recording.status == RecordingStatus.validated)

    entries = [
        {
            "text_fr": sentence.text_fr,
            "text_moore": translation.text_moore,
            "category": sentence.category,
            "audio_original": recording.original_path,
            "audio_cleaned": recording.cleaned_path,
            "duration_ms": recording.duration_ms,
            "silence_trimmed_ms": recording.silence_trimmed_ms,
            "status": recording.status.value,
        }
        for recording, translation, sentence in query.all()
    ]
    db.close()

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)

    print(f"{len(entries)} entrées exportées dans {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output_path")
    parser.add_argument(
        "--all", dest="only_validated", action="store_false",
        help="Inclure aussi les enregistrements non validés",
    )
    parser.set_defaults(only_validated=True)
    args = parser.parse_args()
    export_dataset(args.output_path, args.only_validated)
