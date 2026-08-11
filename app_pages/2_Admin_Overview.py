import streamlit as st

from src import repository
from src.db import SessionLocal

st.title("🛠️ Admin — Overview")

db = SessionLocal()
stats = repository.get_stats(db)
db.close()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Phrases", stats["sentences"])
col2.metric("Traductions", stats["translations"])
col3.metric("Enregistrements", stats["recordings"])
col4.metric("Contributeurs", stats["contributors"])

col5, col6, col7 = st.columns(3)
col5.metric("À réviser", stats["pending_review"])
col6.metric("Validés", stats["validated"])
col7.metric("Rejetés", stats["rejected"])
