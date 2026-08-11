import json

import streamlit as st

from src import repository
from src.db import SessionLocal
from src.models import Recording, RecordingStatus, Sentence, Translation

st.title("📤 Export")

st.subheader("Dataset annoté (phrase, traduction, audio)")

only_validated = st.checkbox("Uniquement les enregistrements validés", value=True)

db = SessionLocal()
query = (
    db.query(Recording, Translation, Sentence)
    .join(Translation, Recording.translation_id == Translation.id)
    .join(Sentence, Translation.sentence_id == Sentence.id)
)
if only_validated:
    query = query.filter(Recording.status == RecordingStatus.validated)

entries = [
    {
        "text_fr": sentence.text_fr,
        "text_moore": translation.text_moore,
        "category": sentence.category,
        "audio_original": recording.original_path,
        "audio_cleaned": recording.cleaned_path,
        "duration_ms": recording.duration_ms,
        "silence_trimmed_ms": recording.silence_trimmed_ms,
        "status": recording.status.value,
    }
    for recording, translation, sentence in query.all()
]

st.write(f"{len(entries)} entrées prêtes à l'export.")

if entries:
    st.download_button(
        "⬇️ Télécharger le dataset (JSON)",
        data=json.dumps(entries, ensure_ascii=False, indent=2),
        file_name="dataset_moore.json",
        mime="application/json",
    )
    st.dataframe(entries, use_container_width=True, hide_index=True)

st.divider()
st.subheader("Phrases encore à traduire")

untranslated = repository.list_untranslated_sentences(db)
db.close()

st.write(f"{len(untranslated)} phrases n'ont encore aucune traduction.")

if untranslated:
    todo_entries = [
        {"text_fr": s.text_fr, "category": s.category, "note": s.note}
        for s in untranslated
    ]
    st.download_button(
        "⬇️ Télécharger les phrases à traduire (JSON)",
        data=json.dumps(todo_entries, ensure_ascii=False, indent=2),
        file_name="phrases_a_traduire.json",
        mime="application/json",
    )
    st.dataframe(todo_entries, use_container_width=True, hide_index=True)
