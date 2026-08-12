import streamlit as st

from src import repository, storage
from src.config import DEFAULT_CATEGORIES
from src.db import SessionLocal
from src.models import RecordingStatus

st.title("🗂️ Gestion des phrases, traductions et audio")

if "gestion_page" not in st.session_state:
    st.session_state.gestion_page = 0

db = SessionLocal()
categories = ["Toutes"] + repository.list_categories(db)

col_search, col_category = st.columns([2, 1])
search = col_search.text_input("Rechercher une phrase", value="")
category = col_category.selectbox("Catégorie", categories)

PAGE_SIZE = 10
offset = st.session_state.gestion_page * PAGE_SIZE

rows, total = repository.list_sentences_with_counts(
    db,
    search=search or None,
    category=None if category == "Toutes" else category,
    limit=PAGE_SIZE,
    offset=offset,
)
db.close()

st.caption(f"{total} phrase(s) correspondent à ce filtre.")

STATUS_LABELS = {"pending": "En attente", "validated": "Validé", "rejected": "Rejeté"}

for sentence, translation_count in rows:
    with st.expander(f"« {sentence.text_fr[:80]} » — {translation_count} traduction(s)"):
        db = SessionLocal()

        st.markdown("**Phrase en français**")
        new_text_fr = st.text_area("Texte", value=sentence.text_fr, key=f"text_fr_{sentence.id}")

        cat_options = DEFAULT_CATEGORIES
        current_index = cat_options.index(sentence.category) if sentence.category in cat_options else len(cat_options) - 1
        new_category = st.selectbox("Catégorie", cat_options, index=current_index, key=f"cat_{sentence.id}")
        new_note = st.text_input("Note", value=sentence.note or "", key=f"note_{sentence.id}")

        col_save, col_confirm, col_delete = st.columns([1, 1, 1])
        if col_save.button("💾 Enregistrer", key=f"save_sentence_{sentence.id}"):
            repository.update_sentence(
                db, sentence.id, text_fr=new_text_fr.strip(), category=new_category, note=new_note.strip() or None
            )
            db.close()
            st.success("Phrase mise à jour.")
            st.rerun()

        confirm_delete = col_confirm.checkbox("Confirmer", key=f"confirm_del_sentence_{sentence.id}")
        if col_delete.button("🗑️ Supprimer tout", key=f"del_sentence_{sentence.id}", disabled=not confirm_delete):
            repository.delete_sentence(db, sentence.id)
            db.close()
            st.success("Phrase, traductions et audio supprimés.")
            st.rerun()

        st.divider()
        st.markdown("**Traductions et audio**")

        translations = repository.get_translations_with_recordings(db, sentence.id)
        if not translations:
            st.caption("Aucune traduction pour l'instant.")

        for translation in translations:
            author = f" — par {translation.contributor.name}" if translation.contributor else ""
            st.caption(f"Traduction{author}")
            new_text_moore = st.text_area(
                "Texte en mooré", value=translation.text_moore, key=f"tm_{translation.id}"
            )

            col_t_save, col_t_delete = st.columns(2)
            if col_t_save.button("💾 Enregistrer", key=f"save_translation_{translation.id}"):
                repository.update_translation_text(db, translation.id, new_text_moore.strip())
                db.close()
                st.success("Traduction mise à jour.")
                st.rerun()
            if col_t_delete.button("🗑️ Supprimer cette traduction", key=f"del_translation_{translation.id}"):
                repository.delete_translation(db, translation.id)
                db.close()
                st.success("Traduction et audio supprimés.")
                st.rerun()

            for recording in translation.recordings:
                st.write(f"Statut actuel : **{STATUS_LABELS.get(recording.status.value, recording.status.value)}**")

                audio_path = recording.cleaned_path or recording.original_path
                try:
                    st.audio(storage.read_audio_file(audio_path))
                    if recording.cleaned_path:
                        st.caption("Version nettoyée (l'originale reste disponible sur disque, non modifiée)")
                except (FileNotFoundError, TypeError):
                    st.warning("Fichier audio introuvable sur disque.")

                col_status, col_apply, col_del_rec = st.columns([2, 1, 1])
                status_values = [s.value for s in RecordingStatus]
                new_status = col_status.selectbox(
                    "Changer le statut",
                    status_values,
                    index=status_values.index(recording.status.value),
                    key=f"status_{recording.id}",
                    label_visibility="collapsed",
                )
                if col_apply.button("Appliquer", key=f"apply_status_{recording.id}"):
                    repository.update_recording_status(db, recording.id, RecordingStatus(new_status))
                    db.close()
                    st.success("Statut mis à jour.")
                    st.rerun()
                if col_del_rec.button("🗑️ Supprimer l'audio", key=f"del_recording_{recording.id}"):
                    repository.delete_recording(db, recording.id)
                    db.close()
                    st.success("Enregistrement supprimé.")
                    st.rerun()

            st.divider()

        db.close()

col_prev, col_page, col_next = st.columns([1, 1, 1])
with col_prev:
    if st.button("← Précédent", disabled=st.session_state.gestion_page == 0):
        st.session_state.gestion_page -= 1
        st.rerun()
with col_page:
    st.write(f"Page {st.session_state.gestion_page + 1}")
with col_next:
    if st.button("Suivant →", disabled=offset + PAGE_SIZE >= total):
        st.session_state.gestion_page += 1
        st.rerun()
