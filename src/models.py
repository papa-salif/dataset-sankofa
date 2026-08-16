import enum
import uuid

from sqlalchemy import Column, DateTime, Enum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.db import Base


class RecordingStatus(str, enum.Enum):
    pending = "pending"
    validated = "validated"
    rejected = "rejected"


class Contributor(Base):
    __tablename__ = "contributors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(120), nullable=False)
    # Identité réelle et unique du contributeur (donnée à l'avance ou générée
    # à la première connexion) — "name" n'est qu'un libellé d'affichage,
    # deux personnes différentes peuvent choisir le même.
    code = Column(String(20), nullable=False, unique=True)
    email = Column(String(200), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    translations = relationship("Translation", back_populates="contributor")
    recordings = relationship("Recording", back_populates="contributor")


class Sentence(Base):
    __tablename__ = "sentences"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    text_fr = Column(Text, nullable=False)
    source = Column(String(200), nullable=True)
    category = Column(String(50), nullable=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    translations = relationship("Translation", back_populates="sentence")


class Translation(Base):
    __tablename__ = "translations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sentence_id = Column(UUID(as_uuid=True), ForeignKey("sentences.id"), nullable=False)
    contributor_id = Column(UUID(as_uuid=True), ForeignKey("contributors.id"), nullable=True)
    # Nul si le contributeur a choisi de ne faire que l'audio pour cette phrase.
    text_moore = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    sentence = relationship("Sentence", back_populates="translations")
    contributor = relationship("Contributor", back_populates="translations")
    recordings = relationship("Recording", back_populates="translation")


class Recording(Base):
    __tablename__ = "recordings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    translation_id = Column(UUID(as_uuid=True), ForeignKey("translations.id"), nullable=False)
    contributor_id = Column(UUID(as_uuid=True), ForeignKey("contributors.id"), nullable=True)

    # Fichier brut, jamais modifié ni transcodé.
    original_path = Column(String(500), nullable=False)
    original_format = Column(String(20), nullable=False)
    sample_rate = Column(Integer, nullable=True)
    duration_ms = Column(Integer, nullable=True)

    # Copie séparée, générée uniquement si un nettoyage a été appliqué.
    cleaned_path = Column(String(500), nullable=True)
    silence_trimmed_ms = Column(Integer, nullable=True)

    status = Column(Enum(RecordingStatus), default=RecordingStatus.pending, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    translation = relationship("Translation", back_populates="recordings")
    contributor = relationship("Contributor", back_populates="recordings")


class Payment(Base):
    """Versement effectué à un contributeur — permet de savoir ce qui a
    réellement été payé, distinct du montant simplement estimé."""

    __tablename__ = "payments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contributor_id = Column(UUID(as_uuid=True), ForeignKey("contributors.id"), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), nullable=True)
    note = Column(String(300), nullable=True)
    # Identité de l'admin ayant enregistré le versement (référence un Contributor,
    # cf. get_or_create_admin_contributor) — pas de relation ORM pour éviter
    # l'ambiguïté des deux FK vers "contributors" sur ce modèle.
    recorded_by_id = Column(UUID(as_uuid=True), ForeignKey("contributors.id"), nullable=True)
    paid_at = Column(DateTime(timezone=True), server_default=func.now())
