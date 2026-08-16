import streamlit as st

from src import repository
from src.config import CURRENCY, DEFAULT_RATE_PER_MINUTE, DEFAULT_RATE_PER_TEXT_TRANSLATION
from src.db import SessionLocal

st.title("💰 Paiements contributeurs")

only_validated = st.checkbox("Audio : uniquement les enregistrements validés", value=True)

col_unit, col_rate, col_text_rate = st.columns(3)
unit = col_unit.radio("Tarif audio par", ["Minute", "Seconde"], horizontal=True)
default_rate = DEFAULT_RATE_PER_MINUTE if unit == "Minute" else DEFAULT_RATE_PER_MINUTE / 60
rate = col_rate.number_input(
    f"Tarif audio par {unit.lower()} ({CURRENCY})", min_value=0.0, value=default_rate, step=1.0
)
text_rate = col_text_rate.number_input(
    f"Tarif par traduction texte ({CURRENCY})",
    min_value=0.0,
    value=DEFAULT_RATE_PER_TEXT_TRANSLATION,
    step=10.0,
)

db = SessionLocal()
overview = repository.list_contributors_overview(db)
db.close()

if not overview:
    st.info("Aucun contributeur pour l'instant.")
    st.stop()

rows = []
total_amount = 0.0
total_duration_ms = 0
total_text_translations = 0

for o in overview:
    if only_validated:
        duration_ms = o["status_summary"]["validated"]["duration_ms"]
        recording_count = o["status_summary"]["validated"]["count"]
    else:
        duration_ms = sum(s["duration_ms"] for s in o["status_summary"].values())
        recording_count = sum(s["count"] for s in o["status_summary"].values())

    total_seconds = duration_ms / 1000
    total_minutes = total_seconds / 60
    audio_amount = rate * (total_minutes if unit == "Minute" else total_seconds)
    text_amount = o["text_translation_count"] * text_rate
    amount = audio_amount + text_amount

    total_amount += amount
    total_duration_ms += duration_ms
    total_text_translations += o["text_translation_count"]

    minutes, seconds = divmod(int(total_seconds), 60)
    rows.append(
        {
            "Contributeur": o["contributor"].name,
            "Code": o["contributor"].code,
            "Enregistrements": recording_count,
            "Durée audio": f"{minutes:02d}:{seconds:02d}",
            "Traductions texte": o["text_translation_count"],
            f"Montant ({CURRENCY})": round(amount, 2),
        }
    )

st.dataframe(rows, use_container_width=True, hide_index=True)

overall_minutes, overall_seconds = divmod(int(total_duration_ms / 1000), 60)
col1, col2, col3 = st.columns(3)
col1.metric("Durée audio totale", f"{overall_minutes:02d}:{overall_seconds:02d}")
col2.metric("Traductions texte totales", total_text_translations)
col3.metric(f"Montant total à verser ({CURRENCY})", round(total_amount, 2))
