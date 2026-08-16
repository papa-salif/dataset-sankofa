import io
import uuid
from typing import Tuple

import cloudinary
import cloudinary.api
import cloudinary.uploader
import cloudinary.utils
import requests
from cloudinary.exceptions import Error as CloudinaryError

from src.config import (
    AUDIO_KEY_PREFIX,
    CLOUDINARY_API_KEY,
    CLOUDINARY_API_SECRET,
    CLOUDINARY_CLOUD_NAME,
)

MIME_TO_EXT = {
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "audio/webm": "webm",
    "audio/ogg": "ogg",
    "audio/mpeg": "mp3",
}

# Les fichiers audio vivent chez Cloudinary (resource_type="raw" : aucune
# transformation/compression, contrairement au traitement par défaut de
# Cloudinary sur les images/vidéos), pas sur le disque local — indispensable
# sur un hébergeur au système de fichiers éphémère (ex. Streamlit Cloud).
# Les colonnes original_path/cleaned_path en base stockent désormais le
# public_id Cloudinary, pas un chemin sur disque.
cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET,
)


def save_original_audio(raw_bytes: bytes, mime_type: str) -> Tuple[str, str]:
    """Sauvegarde les octets tels que reçus du navigateur, sans transcodage."""
    ext = MIME_TO_EXT.get(mime_type, "bin")
    public_id = f"{AUDIO_KEY_PREFIX}/original/{uuid.uuid4()}.{ext}"
    cloudinary.uploader.upload(
        io.BytesIO(raw_bytes),
        public_id=public_id,
        resource_type="raw",
        overwrite=False,
    )
    return public_id, ext


def save_cleaned_audio(cleaned_bytes: bytes, base_id: str) -> str:
    """Sauvegarde la version nettoyée en copie séparée (jamais à la place de l'original)."""
    public_id = f"{AUDIO_KEY_PREFIX}/cleaned/{base_id}_cleaned.wav"
    cloudinary.uploader.upload(
        io.BytesIO(cleaned_bytes),
        public_id=public_id,
        resource_type="raw",
        overwrite=True,
    )
    return public_id


def delete_audio_files(*keys: str) -> None:
    """Supprime les fichiers audio de Cloudinary, sans erreur si déjà absents."""
    for key in keys:
        if not key:
            continue
        try:
            cloudinary.uploader.destroy(key, resource_type="raw")
        except CloudinaryError:
            pass


def _resource_url(key: str) -> str:
    url, _ = cloudinary.utils.cloudinary_url(key, resource_type="raw", secure=True)
    return url


def read_audio_file(key: str) -> bytes:
    if not key:
        raise FileNotFoundError(key)
    response = requests.get(_resource_url(key), timeout=30)
    if response.status_code == 404:
        raise FileNotFoundError(key)
    response.raise_for_status()
    return response.content


def audio_exists(key: str) -> bool:
    if not key:
        return False
    try:
        cloudinary.api.resource(key, resource_type="raw")
        return True
    except CloudinaryError:
        return False
