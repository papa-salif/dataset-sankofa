import streamlit as st

from src import repository, storage
from src.audio_processing import clean_audio, get_duration_ms
from src.db import SessionLocal

MODES = ["Texte + Audio", "Texte seulement", "Audio seulement"]


def init_state():
    defaults = {
        "session_size": 20,
        "session_done": 0,
        "seen_ids": set(),
        "sentence": None,
        "raw_audio": None,
        "cleaned_audio": None,
        "silence_removed_ms": None,
        "contribution_mode": MODES[0],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_for_next_sentence():
    st.session_state.sentence = None
    st.session_state.raw_audio = None
    st.session_state.cleaned_audio = None
    st.session_state.silence_removed_ms = None


init_state()

st.title("🎙️ Espace contributeur")

with st.sidebar:
    st.subheader("Session")
    st.session_state.session_size = st.number_input(
        "Nombre de phrases pour cette session", min_value=1, max_value=200,
        value=st.session_state.session_size,
    )
    st.session_state.contribution_mode = st.radio(
        "Type de contribution",
        MODES,
        index=MODES.index(st.session_state.contribution_mode),
        help="Choisis si tu veux faire seulement le texte, seulement l'audio, ou les deux.",
    )

mode = st.session_state.contribution_mode
want_text = mode in ("Texte + Audio", "Texte seulement")
want_audio = mode in ("Texte + Audio", "Audio seulement")

db = SessionLocal()
contributor_id = st.session_state.contributor_id

# Barre de progression de la session
progress = min(st.session_state.session_done / st.session_state.session_size, 1.0)
st.progress(progress, text=f"{st.session_state.session_done} / {st.session_state.session_size} phrases")

if st.session_state.session_done >= st.session_state.session_size:
    st.success("Session terminée, merci pour ta contribution ! 🎉")
    if st.button("Démarrer une nouvelle session"):
        st.session_state.session_done = 0
        st.session_state.seen_ids = set()
        reset_for_next_sentence()
        st.rerun()
    db.close()
    st.stop()

# Étape 1 : charger une phrase à traduire
if st.session_state.sentence is None:
    st.session_state.sentence = repository.next_sentence_for_contributor(
        db, contributor_id, exclude_ids=st.session_state.seen_ids
    )

sentence = st.session_state.sentence

if sentence is None:
    st.success("Plus aucune phrase disponible pour toi en ce moment. 🎉")
    db.close()
    st.stop()

st.subheader("Phrase en français")
if sentence.category:
    st.caption(f"Catégorie : {sentence.category}")
st.markdown(f"### {sentence.text_fr}")
if sentence.note:
    st.info(f"💡 {sentence.note}")

step_number = 1

if want_audio:
    # La clé change à chaque phrase pour forcer Streamlit à remonter un widget
    # neuf (nouveau flux micro) plutôt que de réutiliser celui de la phrase précédente.
    st.subheader(f"Étape {step_number} — Enregistrement audio")
    step_number += 1
    audio_value = st.audio_input(
        "Enregistre-toi en train de lire la phrase en mooré",
        key=f"audio_input_{sentence.id}",
    )

    if audio_value is not None:
        new_bytes = audio_value.getvalue()
        if not st.session_state.raw_audio or st.session_state.raw_audio["bytes"] != new_bytes:
            st.session_state.raw_audio = {"bytes": new_bytes, "mime": audio_value.type}
            st.session_state.cleaned_audio = None
            st.session_state.silence_removed_ms = None
    else:
        st.session_state.raw_audio = None
        st.session_state.cleaned_audio = None
        st.session_state.silence_removed_ms = None

    if st.session_state.raw_audio:
        st.caption("Enregistrement original (jamais modifié)")
        st.audio(st.session_state.raw_audio["bytes"])

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
else:
    st.session_state.raw_audio = None
    st.session_state.cleaned_audio = None
    st.session_state.silence_removed_ms = None

# Traduction + validation, regroupées dans un formulaire pour que le texte
# tapé soit bien pris en compte au clic, sans devoir cliquer ailleurs ou
# appuyer sur Entrée avant de valider.
st.divider()
st.subheader(f"Étape {step_number} — Traduction en mooré" if want_text else "Validation")

with st.form(key=f"translation_form_{sentence.id}"):
    if want_text:
        translation_text = st.text_area("Écris l'équivalent en mooré", height=100)
    else:
        translation_text = ""
        st.caption("Mode « Audio seulement » : pas de texte à saisir pour cette phrase.")
    col_skip, col_save = st.columns([1, 2])
    skip_clicked = col_skip.form_submit_button("⏭️ Passer cette phrase")
    save_clicked = col_save.form_submit_button("✅ Valider et enregistrer", type="primary")

if skip_clicked:
    st.session_state.seen_ids.add(sentence.id)
    reset_for_next_sentence()
    db.close()
    st.rerun()

if save_clicked:
    clean_text = translation_text.strip() if want_text else None

    if want_text and not clean_text:
        st.error("Écris la traduction en mooré avant de valider.")
    elif want_audio and not st.session_state.raw_audio:
        st.error("Enregistre l'audio avant de valider.")
    else:
        translation = repository.create_translation(
            db,
            sentence_id=sentence.id,
            contributor_id=contributor_id,
            text_moore=clean_text,
        )

        if want_audio and st.session_state.raw_audio:
            original_path, original_format = storage.save_original_audio(
                st.session_state.raw_audio["bytes"], st.session_state.raw_audio["mime"]
            )
            duration_ms = get_duration_ms(st.session_state.raw_audio["bytes"], original_format)

            cleaned_path = None
            if st.session_state.cleaned_audio:
                cleaned_path = storage.save_cleaned_audio(
                    st.session_state.cleaned_audio, base_id=str(translation.id)
                )

            repository.create_recording(
                db,
                translation_id=translation.id,
                contributor_id=contributor_id,
                original_path=original_path,
                original_format=original_format,
                duration_ms=duration_ms,
                cleaned_path=cleaned_path,
                silence_trimmed_ms=st.session_state.silence_removed_ms,
            )

        st.session_state.session_done += 1
        st.session_state.seen_ids.add(sentence.id)
        st.success("Enregistré ! Phrase suivante...")
        reset_for_next_sentence()
        db.close()
        st.rerun()

db.close()
