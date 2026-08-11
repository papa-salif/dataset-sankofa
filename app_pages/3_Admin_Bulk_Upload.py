import streamlit as st

from src import repository
from src.config import DEFAULT_CATEGORIES
from src.db import SessionLocal
from src.importers import parse_uploaded_file

st.title("📥 Import de phrases")

tab_batch, tab_single = st.tabs(["Import en masse", "Saisie unique"])

with tab_batch:
    st.subheader("Ajouter des phrases sources")
    st.caption("Formats supportés : .csv, .json, .txt")

    uploaded_file = st.file_uploader("Dépose un fichier", type=["csv", "json", "txt"])

    if uploaded_file is not None:
        try:
            rows = parse_uploaded_file(uploaded_file.name, uploaded_file.getvalue())
        except ValueError as exc:
            st.error(str(exc))
            rows = []

        if rows:
            st.write(f"{len(rows)} phrases détectées :")
            st.dataframe(rows, use_container_width=True, hide_index=True)

            default_source = st.text_input(
                "Source par défaut (si non précisée dans le fichier)",
                value=uploaded_file.name,
            )

            if st.button("✅ Importer ces phrases", type="primary"):
                db = SessionLocal()
                created = repository.bulk_create_sentences(db, rows, default_source=default_source)
                db.close()
                st.success(f"{created} phrases importées.")
        else:
            st.warning("Aucune phrase valide trouvée dans ce fichier.")

with tab_single:
    st.subheader("Ajouter une phrase")
    text_fr = st.text_area("Phrase en français")
    category = st.selectbox("Catégorie", DEFAULT_CATEGORIES, index=len(DEFAULT_CATEGORIES) - 1)
    note = st.text_input("Note pour le contributeur (optionnel)")
    source = st.text_input("Source (optionnel)")

    if st.button("✅ Ajouter la phrase", disabled=not text_fr.strip()):
        db = SessionLocal()
        repository.bulk_create_sentences(
            db,
            [{"text_fr": text_fr.strip(), "category": category, "note": note or None, "source": source or None}],
        )
        db.close()
        st.success("Phrase ajoutée.")

st.divider()
st.subheader("File d'ingestion récente")

db = SessionLocal()
rows, total = repository.list_sentences_with_counts(db, limit=20)
db.close()

st.caption(f"Affichage des 20 plus récentes sur {total} phrases au total.")
st.dataframe(
    [
        {
            "Phrase (FR)": s.text_fr,
            "Catégorie": s.category or "—",
            "Traductions (Mooré)": count,
        }
        for s, count in rows
    ],
    use_container_width=True,
    hide_index=True,
)
