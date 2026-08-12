import streamlit as st

from src import repository
from src.config import CURRENCY, DEFAULT_RATE_PER_MINUTE
from src.db import SessionLocal

st.title("💰 Paiements contributeurs")

only_validated = st.checkbox("Uniquement les enregistrements validés", value=True)

col_unit, col_rate = st.columns(2)
unit = col_unit.radio("Calculer le tarif par", ["Minute", "Seconde"], horizontal=True)
default_rate = DEFAULT_RATE_PER_MINUTE if unit == "Minute" else DEFAULT_RATE_PER_MINUTE / 60
rate = col_rate.number_input(
    f"Tarif par {unit.lower()} ({CURRENCY})", min_value=0.0, value=default_rate, step=1.0
)

db = SessionLocal()
summary = repository.get_contributor_recording_summary(db, only_validated=only_validated)
db.close()

if not summary:
    st.info("Aucun enregistrement à comptabiliser pour l'instant.")
    st.stop()

rows = []
total_amount = 0.0
total_duration_ms = 0

for contributor, count, duration_ms in summary:
    duration_ms = duration_ms or 0
    total_seconds = duration_ms / 1000
    total_minutes = total_seconds / 60
    amount = rate * (total_minutes if unit == "Minute" else total_seconds)

    total_amount += amount
    total_duration_ms += duration_ms

    minutes, seconds = divmod(int(total_seconds), 60)
    rows.append(
        {
            "Contributeur": contributor.name,
            "Code": contributor.code,
            "Enregistrements": count,
            "Durée": f"{minutes:02d}:{seconds:02d}",
            f"Montant ({CURRENCY})": round(amount, 2),
        }
    )

st.dataframe(rows, use_container_width=True, hide_index=True)

overall_minutes, overall_seconds = divmod(int(total_duration_ms / 1000), 60)
col1, col2 = st.columns(2)
col1.metric("Durée totale", f"{overall_minutes:02d}:{overall_seconds:02d}")
col2.metric(f"Montant total à verser ({CURRENCY})", round(total_amount, 2))
