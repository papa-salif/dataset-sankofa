import streamlit as st

from src import repository
from src.db import SessionLocal

st.title("📝 File de traduction")

if "queue_page" not in st.session_state:
    st.session_state.queue_page = 0

db = SessionLocal()
categories = ["Toutes"] + repository.list_categories(db)

col_search, col_category = st.columns([2, 1])
search = col_search.text_input("Rechercher une phrase", value="")
category = col_category.selectbox("Catégorie", categories)

PAGE_SIZE = 20
offset = st.session_state.queue_page * PAGE_SIZE

rows, total = repository.list_sentences_with_counts(
    db,
    search=search or None,
    category=None if category == "Toutes" else category,
    limit=PAGE_SIZE,
    offset=offset,
)
db.close()

st.caption(f"{total} phrases correspondent à ce filtre.")
st.dataframe(
    [
        {
            "Phrase (FR)": s.text_fr,
            "Catégorie": s.category or "—",
            "Traductions (Mooré)": count,
            "Statut": "Sans traduction" if count == 0 else "Traduite",
        }
        for s, count in rows
    ],
    use_container_width=True,
    hide_index=True,
)

col_prev, col_page, col_next = st.columns([1, 1, 1])
with col_prev:
    if st.button("← Précédent", disabled=st.session_state.queue_page == 0):
        st.session_state.queue_page -= 1
        st.rerun()
with col_page:
    st.write(f"Page {st.session_state.queue_page + 1}")
with col_next:
    if st.button("Suivant →", disabled=offset + PAGE_SIZE >= total):
        st.session_state.queue_page += 1
        st.rerun()
