import io
import json
import os
import zipfile
from typing import List, Tuple

from sqlalchemy.orm import Session

from src.models import Recording, RecordingStatus, Sentence, Translation


def _query_dataset(db: Session, only_validated: bool):
    query = (
        db.query(Recording, Translation, Sentence)
        .join(Translation, Recording.translation_id == Translation.id)
        .join(Sentence, Translation.sentence_id == Sentence.id)
    )
    if only_validated:
        query = query.filter(Recording.status == RecordingStatus.validated)
    return query.order_by(Sentence.created_at.asc()).all()


def build_dataset_entries(db: Session, only_validated: bool = True) -> List[dict]:
    """Métadonnées seules (chemins serveur, pas les fichiers) — utile pour un
    aperçu rapide, mais pas pour déplacer le dataset ailleurs."""
    return [
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
        for recording, translation, sentence in _query_dataset(db, only_validated)
    ]


def build_dataset_zip(db: Session, only_validated: bool = True) -> Tuple[bytes, int]:
    """Archive ZIP autonome (manifest.json + fichiers audio), prête à être
    déplacée/importée dans un pipeline d'entraînement. Utilise la version
    nettoyée quand elle existe, sinon l'original. Retourne (zip_bytes,
    nombre d'entrées ignorées car le fichier audio n'existe plus sur disque)."""
    rows = _query_dataset(db, only_validated)

    manifest = []
    skipped = 0
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for recording, translation, sentence in rows:
            used_cleaned = bool(recording.cleaned_path and os.path.exists(recording.cleaned_path))
            source_path = recording.cleaned_path if used_cleaned else recording.original_path

            if not source_path or not os.path.exists(source_path):
                skipped += 1
                continue

            ext = "wav" if used_cleaned else recording.original_format
            archive_name = f"audio/{recording.id}.{ext}"
            zf.write(source_path, arcname=archive_name)

            manifest.append(
                {
                    "text_fr": sentence.text_fr,
                    "text_moore": translation.text_moore,
                    "category": sentence.category,
                    "audio_filename": archive_name,
                    "audio_source": "cleaned" if used_cleaned else "original",
                    "duration_ms": recording.duration_ms,
                    "status": recording.status.value,
                }
            )

        zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))

    buffer.seek(0)
    return buffer.getvalue(), skipped
