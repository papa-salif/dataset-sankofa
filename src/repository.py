from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from src.models import Contributor, Recording, RecordingStatus, Sentence, Translation


def get_or_create_contributor(db: Session, name: str) -> Contributor:
    contributor = db.query(Contributor).filter_by(name=name).first()
    if contributor:
        return contributor
    contributor = Contributor(name=name)
    db.add(contributor)
    db.commit()
    db.refresh(contributor)
    return contributor


def next_sentence_without_translation(db: Session) -> Optional[Sentence]:
    return (
        db.query(Sentence)
        .filter(~Sentence.translations.any())
        .order_by(Sentence.created_at)
        .first()
    )


def create_translation(
    db: Session, sentence_id: UUID, contributor_id: UUID, text_moore: str
) -> Translation:
    translation = Translation(
        sentence_id=sentence_id,
        contributor_id=contributor_id,
        text_moore=text_moore,
    )
    db.add(translation)
    db.commit()
    db.refresh(translation)
    return translation


def create_recording(
    db: Session,
    translation_id: UUID,
    contributor_id: UUID,
    original_path: str,
    original_format: str,
    duration_ms: Optional[int] = None,
    sample_rate: Optional[int] = None,
    cleaned_path: Optional[str] = None,
    silence_trimmed_ms: Optional[int] = None,
) -> Recording:
    recording = Recording(
        translation_id=translation_id,
        contributor_id=contributor_id,
        original_path=original_path,
        original_format=original_format,
        duration_ms=duration_ms,
        sample_rate=sample_rate,
        cleaned_path=cleaned_path,
        silence_trimmed_ms=silence_trimmed_ms,
        status=RecordingStatus.pending,
    )
    db.add(recording)
    db.commit()
    db.refresh(recording)
    return recording
