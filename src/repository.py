from typing import List, Optional, Sequence, Tuple
from uuid import UUID

from sqlalchemy import func
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


def next_sentence_for_contributor(
    db: Session, contributor_id: UUID, exclude_ids: Optional[Sequence[UUID]] = None
) -> Optional[Sentence]:
    """Choisit la phrase à proposer : jamais une phrase déjà traduite par ce
    contributeur, en priorisant celles ayant le moins de traductions au total
    (pour équilibrer la couverture entre plusieurs contributeurs)."""
    translation_counts = (
        db.query(Translation.sentence_id, func.count(Translation.id).label("cnt"))
        .group_by(Translation.sentence_id)
        .subquery()
    )
    already_done = db.query(Translation.sentence_id).filter(
        Translation.contributor_id == contributor_id
    )

    query = (
        db.query(Sentence)
        .outerjoin(translation_counts, Sentence.id == translation_counts.c.sentence_id)
        .filter(~Sentence.id.in_(already_done))
    )
    if exclude_ids:
        query = query.filter(~Sentence.id.in_(list(exclude_ids)))

    return query.order_by(
        func.coalesce(translation_counts.c.cnt, 0).asc(), Sentence.created_at.asc()
    ).first()


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


def bulk_create_sentences(
    db: Session, rows: Sequence[dict], default_source: Optional[str] = None
) -> int:
    """Insère une liste de dicts {text_fr, category, note, source} sans toucher
    aux phrases déjà présentes. Retourne le nombre de phrases créées."""
    created = 0
    for row in rows:
        db.add(
            Sentence(
                text_fr=row["text_fr"],
                category=row.get("category"),
                note=row.get("note"),
                source=row.get("source") or default_source,
            )
        )
        created += 1
    db.commit()
    return created


def list_categories(db: Session) -> List[str]:
    rows = db.query(Sentence.category).distinct().all()
    return sorted({c for (c,) in rows if c})


def list_sentences_with_counts(
    db: Session,
    search: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Tuple[List[Tuple[Sentence, int]], int]:
    """Retourne (liste de (phrase, nombre_de_traductions), total) pour la file de traduction."""
    translation_counts = (
        db.query(Translation.sentence_id, func.count(Translation.id).label("cnt"))
        .group_by(Translation.sentence_id)
        .subquery()
    )
    query = db.query(Sentence, func.coalesce(translation_counts.c.cnt, 0)).outerjoin(
        translation_counts, Sentence.id == translation_counts.c.sentence_id
    )
    if search:
        query = query.filter(Sentence.text_fr.ilike(f"%{search}%"))
    if category:
        query = query.filter(Sentence.category == category)

    total = query.count()
    rows = (
        query.order_by(Sentence.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return rows, total


def list_untranslated_sentences(db: Session) -> List[Sentence]:
    """Phrases sans aucune traduction — celles qui restent « à traduire »."""
    return (
        db.query(Sentence)
        .filter(~Sentence.translations.any())
        .order_by(Sentence.created_at.asc())
        .all()
    )


def next_recording_for_review(
    db: Session, status: RecordingStatus = RecordingStatus.pending
) -> Optional[Recording]:
    return (
        db.query(Recording)
        .filter(Recording.status == status)
        .order_by(Recording.created_at.asc())
        .first()
    )


def validate_all_pending_recordings(db: Session) -> int:
    """Valide en une fois tous les enregistrements en attente de révision
    (sans passer par Trim/Normalize individuel). Retourne le nombre validé."""
    updated = (
        db.query(Recording)
        .filter(Recording.status == RecordingStatus.pending)
        .update({Recording.status: RecordingStatus.validated}, synchronize_session=False)
    )
    db.commit()
    return updated


def update_recording_status(
    db: Session, recording_id: UUID, status: RecordingStatus
) -> Optional[Recording]:
    recording = db.query(Recording).filter_by(id=recording_id).first()
    if recording:
        recording.status = status
        db.commit()
        db.refresh(recording)
    return recording


def update_recording_cleaned_audio(
    db: Session,
    recording_id: UUID,
    cleaned_path: str,
    silence_trimmed_ms: Optional[int] = None,
) -> Optional[Recording]:
    recording = db.query(Recording).filter_by(id=recording_id).first()
    if recording:
        recording.cleaned_path = cleaned_path
        if silence_trimmed_ms is not None:
            recording.silence_trimmed_ms = silence_trimmed_ms
        db.commit()
        db.refresh(recording)
    return recording


def get_stats(db: Session) -> dict:
    return {
        "sentences": db.query(func.count(Sentence.id)).scalar(),
        "translations": db.query(func.count(Translation.id)).scalar(),
        "recordings": db.query(func.count(Recording.id)).scalar(),
        "pending_review": db.query(func.count(Recording.id))
        .filter(Recording.status == RecordingStatus.pending)
        .scalar(),
        "validated": db.query(func.count(Recording.id))
        .filter(Recording.status == RecordingStatus.validated)
        .scalar(),
        "rejected": db.query(func.count(Recording.id))
        .filter(Recording.status == RecordingStatus.rejected)
        .scalar(),
        "contributors": db.query(func.count(Contributor.id)).scalar(),
    }
