import streamlit as st

from src import repository, storage
from src.audio_processing import clean_audio
from src.db import SessionLocal

st.set_page_config(page_title="Collecte Français → Mooré", page_icon="🎙️")


def init_state():
    defaults = {
        "contributor_name": "",
        "sentence": None,
        "translation_text": "",
        "raw_audio": None,
        "cleaned_audio": None,
        "silence_removed_ms": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_for_next_sentence():
    st.session_state.sentence = None
    st.session_state.translation_text = ""
    st.session_state.raw_audio = None
    st.session_state.cleaned_audio = None
    st.session_state.silence_removed_ms = None


init_state()

st.title("🎙️ Collecte de données Français → Mooré")

with st.sidebar:
    st.subheader("Contributeur")
    name = st.text_input("Ton nom", value=st.session_state.contributor_name)
    if name:
        st.session_state.contributor_name = name

if not st.session_state.contributor_name:
    st.info("Renseigne ton nom dans la barre latérale pour commencer.")
    st.stop()

db = SessionLocal()
contributor = repository.get_or_create_contributor(db, st.session_state.contributor_name)

# Étape 1 : charger une phrase à traduire
if st.session_state.sentence is None:
    st.session_state.sentence = repository.next_sentence_without_translation(db)

sentence = st.session_state.sentence

if sentence is None:
    st.success("Toutes les phrases disponibles ont été traduites. 🎉")
    db.close()
    st.stop()

st.subheader("Phrase en français")
st.markdown(f"### {sentence.text_fr}")

# Étape 2 : traduction en mooré
st.subheader("Traduction en mooré")
st.session_state.translation_text = st.text_area(
    "Écris l'équivalent en mooré",
    value=st.session_state.translation_text,
    height=100,
)

# Étape 3 : enregistrement audio
st.subheader("Enregistrement audio")
audio_value = st.audio_input("Enregistre-toi en train de lire la phrase en mooré")

if audio_value is not None:
    new_bytes = audio_value.getvalue()
    if not st.session_state.raw_audio or st.session_state.raw_audio["bytes"] != new_bytes:
        st.session_state.raw_audio = {"bytes": new_bytes, "mime": audio_value.type}
        st.session_state.cleaned_audio = None
        st.session_state.silence_removed_ms = None

if st.session_state.raw_audio:
    st.caption("Enregistrement original (jamais modifié)")
    st.audio(st.session_state.raw_audio["bytes"])

    # Étape 4 : nettoyage des silences (optionnel, copie séparée)
    if st.button("🧹 Nettoyer les silences"):
        ext = storage.MIME_TO_EXT.get(st.session_state.raw_audio["mime"], "wav")
        cleaned_bytes, silence_removed_ms = clean_audio(
            st.session_state.raw_audio["bytes"], ext
        )
        st.session_state.cleaned_audio = cleaned_bytes
        st.session_state.silence_removed_ms = silence_removed_ms

    if st.session_state.cleaned_audio:
        st.caption(f"Version nettoyée — silence réduit de {st.session_state.silence_removed_ms} ms")
        st.audio(st.session_state.cleaned_audio)

# Étape 5 : validation et enregistrement
st.divider()
can_save = bool(st.session_state.translation_text.strip()) and bool(st.session_state.raw_audio)

if st.button("✅ Valider et enregistrer", disabled=not can_save, type="primary"):
    translation = repository.create_translation(
        db,
        sentence_id=sentence.id,
        contributor_id=contributor.id,
        text_moore=st.session_state.translation_text.strip(),
    )

    original_path, original_format = storage.save_original_audio(
        st.session_state.raw_audio["bytes"], st.session_state.raw_audio["mime"]
    )

    cleaned_path = None
    if st.session_state.cleaned_audio:
        cleaned_path = storage.save_cleaned_audio(
            st.session_state.cleaned_audio, base_id=str(translation.id)
        )

    repository.create_recording(
        db,
        translation_id=translation.id,
        contributor_id=contributor.id,
        original_path=original_path,
        original_format=original_format,
        cleaned_path=cleaned_path,
        silence_trimmed_ms=st.session_state.silence_removed_ms,
    )

    st.success("Enregistré ! Phrase suivante...")
    reset_for_next_sentence()
    db.close()
    st.rerun()

db.close()
