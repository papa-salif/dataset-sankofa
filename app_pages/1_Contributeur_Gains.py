import streamlit as st

from src import repository
from src.config import CURRENCY, DEFAULT_RATE_PER_MINUTE
from src.db import SessionLocal


def format_duration(duration_ms: int) -> str:
    total_seconds = int(duration_ms / 1000)
    minutes, seconds = divmod(total_seconds, 60)
    return f"{minutes:02d}:{seconds:02d}"


st.title("💰 Mes gains")

db = SessionLocal()
summary = repository.get_contributor_own_summary(db, st.session_state.contributor_id)
db.close()

validated = summary["validated"]
pending = summary["pending"]
rejected = summary["rejected"]

col1, col2, col3 = st.columns(3)
col1.metric("Enregistrements validés", validated["count"])
col2.metric("Durée validée", format_duration(validated["duration_ms"]))

if DEFAULT_RATE_PER_MINUTE > 0:
    amount = DEFAULT_RATE_PER_MINUTE * (validated["duration_ms"] / 1000 / 60)
    col3.metric(f"Montant estimé ({CURRENCY})", round(amount, 2))
    st.caption(f"Calculé au tarif de {DEFAULT_RATE_PER_MINUTE} {CURRENCY} / minute.")
else:
    col3.metric(f"Montant estimé ({CURRENCY})", "—")
    st.warning("Le tarif n'a pas encore été configuré par l'administrateur.")

if pending["count"]:
    st.info(
        f"⏳ {pending['count']} enregistrement(s) en attente de révision "
        f"({format_duration(pending['duration_ms'])}) — pas encore comptés."
    )
if rejected["count"]:
    st.caption(
        f"❌ {rejected['count']} enregistrement(s) rejeté(s) "
        f"({format_duration(rejected['duration_ms'])}), non comptés."
    )
