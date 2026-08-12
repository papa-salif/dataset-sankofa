import json

import streamlit as st

from src import repository
from src.db import SessionLocal
from src.export_utils import build_dataset_entries, build_dataset_zip

st.title("📤 Export")

st.subheader("Dataset annoté (phrase, traduction, audio)")

only_validated = st.checkbox("Uniquement les enregistrements validés", value=True)

db = SessionLocal()
entries = build_dataset_entries(db, only_validated=only_validated)
zip_bytes, skipped = build_dataset_zip(db, only_validated=only_validated)
db.close()

st.write(f"{len(entries)} entrées prêtes à l'export.")
if skipped:
    st.warning(f"{skipped} enregistrement(s) ignoré(s) dans le ZIP : fichier audio introuvable sur disque.")

if entries:
    col_zip, col_json = st.columns(2)
    col_zip.download_button(
        "📦 Télécharger l'archive complète (ZIP + audio)",
        data=zip_bytes,
        file_name="dataset_moore.zip",
        mime="application/zip",
        type="primary",
        help="Recommandé pour l'entraînement : contient un manifest.json et tous les fichiers audio.",
    )
    col_json.download_button(
        "⬇️ Métadonnées seules (JSON, sans audio)",
        data=json.dumps(entries, ensure_ascii=False, indent=2),
        file_name="dataset_moore.json",
        mime="application/json",
    )
    st.dataframe(entries, use_container_width=True, hide_index=True)

st.divider()
st.subheader("Phrases encore à traduire")

db = SessionLocal()
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
