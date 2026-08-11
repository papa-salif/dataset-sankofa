import io
from typing import Tuple

from pydub import AudioSegment
from pydub.effects import normalize as _pydub_normalize
from pydub.silence import detect_leading_silence, detect_silence


def _trim_edges(sound: AudioSegment, silence_threshold_db: float = -40.0) -> AudioSegment:
    start_trim = detect_leading_silence(sound, silence_threshold=silence_threshold_db)
    end_trim = detect_leading_silence(sound.reverse(), silence_threshold=silence_threshold_db)
    duration = len(sound)
    return sound[start_trim: duration - end_trim]


def _cap_internal_silences(
    sound: AudioSegment,
    silence_threshold_db: float = -40.0,
    min_silence_len_ms: int = 400,
    max_kept_silence_ms: int = 300,
) -> AudioSegment:
    """Raccourcit les silences internes trop longs sans les supprimer entièrement,
    pour garder un débit de parole naturel (utile pour l'entraînement ASR/TTS)."""
    silences = detect_silence(
        sound, min_silence_len=min_silence_len_ms, silence_thresh=silence_threshold_db
    )
    if not silences:
        return sound

    result = AudioSegment.empty()
    cursor = 0
    for start, end in silences:
        result += sound[cursor:start]
        kept_silence = min(end - start, max_kept_silence_ms)
        result += sound[start : start + kept_silence]
        cursor = end
    result += sound[cursor:]
    return result


def clean_audio(raw_bytes: bytes, original_format: str) -> Tuple[bytes, int]:
    """Nettoie l'audio (silences en bordure + silences internes trop longs).

    Ne modifie jamais le fichier original : lit les octets bruts et retourne
    une nouvelle version en WAV, à sauvegarder en copie séparée.

    Retourne (audio_nettoye_wav_bytes, duree_silence_supprimee_ms).
    """
    sound = AudioSegment.from_file(io.BytesIO(raw_bytes), format=original_format)
    original_duration = len(sound)

    trimmed = _trim_edges(sound)
    capped = _cap_internal_silences(trimmed)

    silence_removed_ms = original_duration - len(capped)

    buffer = io.BytesIO()
    capped.export(buffer, format="wav")
    return buffer.getvalue(), silence_removed_ms


def apply_trim(raw_bytes: bytes, original_format: str) -> Tuple[bytes, int]:
    """Alias explicite de clean_audio, utilisé côté admin (bouton « Trim »)."""
    return clean_audio(raw_bytes, original_format)


def apply_normalize(raw_bytes: bytes, original_format: str) -> bytes:
    """Normalise le volume (gain uniforme jusqu'au niveau max sans écrêtage).
    Ne modifie jamais le fichier original : retourne une nouvelle version en WAV."""
    sound = AudioSegment.from_file(io.BytesIO(raw_bytes), format=original_format)
    normalized = _pydub_normalize(sound)
    buffer = io.BytesIO()
    normalized.export(buffer, format="wav")
    return buffer.getvalue()


def get_duration_ms(raw_bytes: bytes, original_format: str) -> int:
    sound = AudioSegment.from_file(io.BytesIO(raw_bytes), format=original_format)
    return len(sound)
