import streamlit as st

from src import repository, storage
from src.audio_processing import apply_normalize, apply_trim
from src.db import SessionLocal
from src.models import RecordingStatus

st.title("🎧 Audio Lab — révision des enregistrements")


def load_working_audio(recording):
    """(ré)initialise l'audio de travail à partir de la version nettoyée
    si elle existe, sinon de l'original. Ne modifie jamais le fichier original."""
    original_bytes = storage.read_audio_file(recording.original_path)

    if recording.cleaned_path and storage.audio_exists(recording.cleaned_path):
        working_bytes = storage.read_audio_file(recording.cleaned_path)
        working_format = "wav"
        is_modified = True
    else:
        working_bytes = original_bytes
        working_format = recording.original_format
        is_modified = False

    st.session_state.lab_recording_id = recording.id
    st.session_state.lab_original_bytes = original_bytes
    st.session_state.lab_original_format = recording.original_format
    st.session_state.lab_working_bytes = working_bytes
    st.session_state.lab_working_format = working_format
    st.session_state.lab_is_modified = is_modified
    st.session_state.lab_silence_removed_ms = recording.silence_trimmed_ms


db = SessionLocal()
pending_count = repository.get_stats(db)["pending_review"]

with st.expander(f"✅ Valider tous les enregistrements en attente ({pending_count})"):
    st.caption(
        "Valide directement tous les enregistrements en attente, sans passer "
        "par la révision individuelle (Trim/Normalize) ci-dessous."
    )
    confirm_bulk = st.checkbox("Je confirme vouloir tout valider", key="confirm_bulk_validate")
    if st.button(
        "Valider tout", disabled=not confirm_bulk or pending_count == 0, type="primary"
    ):
        validated_count = repository.validate_all_pending_recordings(db)
        db.close()
        st.success(f"{validated_count} enregistrement(s) validé(s).")
        for key in ["lab_recording_id", "lab_original_bytes", "lab_original_format",
                    "lab_working_bytes", "lab_working_format", "lab_is_modified", "lab_silence_removed_ms"]:
            st.session_state.pop(key, None)
        st.rerun()

st.divider()

recording = repository.next_recording_for_review(db)

if recording is None:
    st.success("Aucun enregistrement en attente de révision. 🎉")
    db.close()
    st.stop()

if st.session_state.get("lab_recording_id") != recording.id:
    load_working_audio(recording)

sentence = recording.translation.sentence
translation = recording.translation

st.caption(f"Élément #{str(sentence.id)[:8]} · en attente de révision")
st.markdown(f"### « {sentence.text_fr} »")
if sentence.category:
    st.caption(f"Catégorie : {sentence.category}")

st.subheader("Traduction en mooré")
st.write(translation.text_moore or "_(pas de texte fourni, audio seulement)_")
if recording.contributor:
    st.caption(f"Par {recording.contributor.name}")

st.subheader("Audio")
st.audio(st.session_state.lab_working_bytes)
if st.session_state.lab_is_modified:
    st.caption("Version actuelle : nettoyée (l'original reste inchangé sur disque)")
else:
    st.caption("Version actuelle : originale, telle qu'enregistrée")

st.markdown("**Outils audio**")
col_trim, col_normalize, col_reset = st.columns(3)

with col_trim:
    if st.button("✂️ Trim"):
        cleaned_bytes, silence_removed_ms = apply_trim(
            st.session_state.lab_working_bytes, st.session_state.lab_working_format
        )
        st.session_state.lab_working_bytes = cleaned_bytes
        st.session_state.lab_working_format = "wav"
        st.session_state.lab_is_modified = True
        st.session_state.lab_silence_removed_ms = silence_removed_ms
        st.rerun()

with col_normalize:
    if st.button("📶 Normalize"):
        normalized_bytes = apply_normalize(
            st.session_state.lab_working_bytes, st.session_state.lab_working_format
        )
        st.session_state.lab_working_bytes = normalized_bytes
        st.session_state.lab_working_format = "wav"
        st.session_state.lab_is_modified = True
        st.rerun()

with col_reset:
    if st.button("↺ Repartir de l'original"):
        st.session_state.lab_working_bytes = st.session_state.lab_original_bytes
        st.session_state.lab_working_format = st.session_state.lab_original_format
        st.session_state.lab_is_modified = False
        st.session_state.lab_silence_removed_ms = None
        st.rerun()

st.divider()
col_reject, col_approve = st.columns(2)

with col_reject:
    if st.button("❌ Reject", use_container_width=True):
        repository.update_recording_status(db, recording.id, RecordingStatus.rejected)
        db.close()
        for key in ["lab_recording_id", "lab_original_bytes", "lab_original_format",
                    "lab_working_bytes", "lab_working_format", "lab_is_modified", "lab_silence_removed_ms"]:
            st.session_state.pop(key, None)
        st.rerun()

with col_approve:
    if st.button("✅ Approve", type="primary", use_container_width=True):
        if st.session_state.lab_is_modified:
            cleaned_path = storage.save_cleaned_audio(
                st.session_state.lab_working_bytes, base_id=str(recording.id)
            )
            repository.update_recording_cleaned_audio(
                db, recording.id, cleaned_path, st.session_state.lab_silence_removed_ms
            )
        repository.update_recording_status(db, recording.id, RecordingStatus.validated)
        db.close()
        for key in ["lab_recording_id", "lab_original_bytes", "lab_original_format",
                    "lab_working_bytes", "lab_working_format", "lab_is_modified", "lab_silence_removed_ms"]:
            st.session_state.pop(key, None)
        st.rerun()

db.close()
