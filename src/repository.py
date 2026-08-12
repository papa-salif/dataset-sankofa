import secrets
from typing import List, Optional, Sequence, Tuple
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from src import storage
from src.models import Contributor, Recording, RecordingStatus, Sentence, Translation

# Alphabet sans caractères ambigus (pas de 0/O, 1/I/L) pour que le code reste
# facile à relire/retaper à la main.
_CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def generate_unique_contributor_code(db: Session) -> str:
    for _ in range(50):
        code = "CTR-" + "".join(secrets.choice(_CODE_ALPHABET) for _ in range(4))
        if not db.query(Contributor).filter_by(code=code).first():
            return code
    raise RuntimeError("Impossible de générer un code contributeur unique.")


def create_contributor(db: Session, name: str) -> Contributor:
    """Crée un nouveau contributeur avec un code unique généré automatiquement.
    C'est ce code, pas le nom affiché, qui identifie réellement la personne."""
    contributor = Contributor(name=name, code=generate_unique_contributor_code(db))
    db.add(contributor)
    db.commit()
    db.refresh(contributor)
    return contributor


def get_contributor_by_code(db: Session, code: str) -> Optional[Contributor]:
    return db.query(Contributor).filter_by(code=code.strip().upper()).first()


def get_contributor_by_id(db: Session, contributor_id: UUID) -> Optional[Contributor]:
    return db.query(Contributor).filter_by(id=contributor_id).first()


def find_contributors_by_name(db: Session, name: str) -> List[Contributor]:
    """Utilisé pour retrouver un code oublié : recherche par nom affiché
    (plusieurs comptes peuvent partager le même nom)."""
    return (
        db.query(Contributor)
        .filter(Contributor.name.ilike(name.strip()))
        .order_by(Contributor.created_at.asc())
        .all()
    )


def get_or_create_admin_contributor(db: Session) -> Contributor:
    """Identité réservée utilisée quand un admin contribue lui-même via
    l'espace Contribuer — un seul slot fixe, pas de code à retenir."""
    contributor = db.query(Contributor).filter_by(name="Admin").first()
    if contributor:
        return contributor
    return create_contributor(db, "Admin")


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


def get_contributor_recording_summary(
    db: Session, only_validated: bool = True
) -> List[Tuple[Contributor, int, int]]:
    """Retourne, par contributeur, (contributor, nombre d'enregistrements,
    durée totale en ms) — sert de base au calcul du montant à verser."""
    query = (
        db.query(
            Contributor,
            func.count(Recording.id),
            func.coalesce(func.sum(Recording.duration_ms), 0),
        )
        .join(Recording, Recording.contributor_id == Contributor.id)
    )
    if only_validated:
        query = query.filter(Recording.status == RecordingStatus.validated)
    return (
        query.group_by(Contributor.id)
        .order_by(func.coalesce(func.sum(Recording.duration_ms), 0).desc())
        .all()
    )


def get_contributor_own_summary(db: Session, contributor_id: UUID) -> dict:
    """Répartition des enregistrements d'UN contributeur par statut, avec la
    durée totale par statut (en ms) — sert à lui montrer ses propres gains."""
    rows = (
        db.query(
            Recording.status,
            func.count(Recording.id),
            func.coalesce(func.sum(Recording.duration_ms), 0),
        )
        .filter(Recording.contributor_id == contributor_id)
        .group_by(Recording.status)
        .all()
    )
    summary = {status.value: {"count": 0, "duration_ms": 0} for status in RecordingStatus}
    for status, count, duration_ms in rows:
        summary[status.value] = {"count": count, "duration_ms": duration_ms}
    return summary


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


def get_translations_with_recordings(db: Session, sentence_id: UUID) -> List[Translation]:
    return (
        db.query(Translation)
        .filter(Translation.sentence_id == sentence_id)
        .order_by(Translation.created_at.asc())
        .all()
    )


def update_sentence(
    db: Session,
    sentence_id: UUID,
    text_fr: str,
    category: Optional[str],
    note: Optional[str],
) -> Optional[Sentence]:
    sentence = db.query(Sentence).filter_by(id=sentence_id).first()
    if not sentence:
        return None
    sentence.text_fr = text_fr
    sentence.category = category
    sentence.note = note
    db.commit()
    db.refresh(sentence)
    return sentence


def update_translation_text(
    db: Session, translation_id: UUID, text_moore: str
) -> Optional[Translation]:
    translation = db.query(Translation).filter_by(id=translation_id).first()
    if not translation:
        return None
    translation.text_moore = text_moore
    db.commit()
    db.refresh(translation)
    return translation


def delete_recording(db: Session, recording_id: UUID) -> bool:
    recording = db.query(Recording).filter_by(id=recording_id).first()
    if not recording:
        return False
    storage.delete_audio_files(recording.original_path, recording.cleaned_path)
    db.delete(recording)
    db.commit()
    return True


def delete_translation(db: Session, translation_id: UUID) -> bool:
    translation = db.query(Translation).filter_by(id=translation_id).first()
    if not translation:
        return False
    for recording in list(translation.recordings):
        storage.delete_audio_files(recording.original_path, recording.cleaned_path)
        db.delete(recording)
    db.delete(translation)
    db.commit()
    return True


def delete_sentence(db: Session, sentence_id: UUID) -> bool:
    sentence = db.query(Sentence).filter_by(id=sentence_id).first()
    if not sentence:
        return False
    for translation in list(sentence.translations):
        for recording in list(translation.recordings):
            storage.delete_audio_files(recording.original_path, recording.cleaned_path)
            db.delete(recording)
        db.delete(translation)
    db.delete(sentence)
    db.commit()
    return True


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
