import os
import uuid
from typing import Tuple

from src.config import AUDIO_CLEANED_DIR, AUDIO_ORIGINAL_DIR

os.makedirs(AUDIO_ORIGINAL_DIR, exist_ok=True)
os.makedirs(AUDIO_CLEANED_DIR, exist_ok=True)

MIME_TO_EXT = {
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "audio/webm": "webm",
    "audio/ogg": "ogg",
    "audio/mpeg": "mp3",
}


def save_original_audio(raw_bytes: bytes, mime_type: str) -> Tuple[str, str]:
    """Sauvegarde les octets tels que reçus du navigateur, sans transcodage."""
    ext = MIME_TO_EXT.get(mime_type, "bin")
    filename = f"{uuid.uuid4()}.{ext}"
    path = f"{AUDIO_ORIGINAL_DIR}/{filename}"
    with open(path, "wb") as f:
        f.write(raw_bytes)
    return path, ext


def save_cleaned_audio(cleaned_bytes: bytes, base_id: str) -> str:
    """Sauvegarde la version nettoyée en copie séparée (jamais à la place de l'original)."""
    filename = f"{base_id}_cleaned.wav"
    path = f"{AUDIO_CLEANED_DIR}/{filename}"
    with open(path, "wb") as f:
        f.write(cleaned_bytes)
    return path


def delete_audio_files(*paths: str) -> None:
    """Supprime les fichiers audio du disque, sans erreur si déjà absents."""
    for path in paths:
        if path and os.path.exists(path):
            os.remove(path)


def read_audio_file(path: str) -> bytes:
    with open(path, "rb") as f:
        return f.read()
