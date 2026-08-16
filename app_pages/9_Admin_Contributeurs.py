import streamlit as st

from src import repository, storage
from src.config import CURRENCY, DEFAULT_RATE_PER_MINUTE, DEFAULT_RATE_PER_TEXT_TRANSLATION
from src.db import SessionLocal
from src.export_utils import build_dataset_zip


def format_duration(duration_ms: int) -> str:
    total_seconds = int((duration_ms or 0) / 1000)
    minutes, seconds = divmod(total_seconds, 60)
    return f"{minutes:02d}:{seconds:02d}"


def estimate_amount(duration_ms: int, text_translation_count: int = 0) -> float:
    audio_amount = DEFAULT_RATE_PER_MINUTE * ((duration_ms or 0) / 1000 / 60)
    text_amount = text_translation_count * DEFAULT_RATE_PER_TEXT_TRANSLATION
    return audio_amount + text_amount


st.title("👥 Contributeurs")

if "selected_contributor_id" not in st.session_state:
    st.session_state.selected_contributor_id = None

db = SessionLocal()

# ---------------------------------------------------------------- Fiche détail
if st.session_state.selected_contributor_id is not None:
    contributor = repository.get_contributor_by_id(db, st.session_state.selected_contributor_id)

    if contributor is None:
        st.error("Contributeur introuvable.")
        st.session_state.selected_contributor_id = None
        db.close()
        st.stop()

    if st.button("← Retour à la liste"):
        st.session_state.selected_contributor_id = None
        db.close()
        st.rerun()

    st.subheader(f"{contributor.name} — `{contributor.code}`")
    st.caption(f"Contributeur depuis le {contributor.created_at:%d/%m/%Y}")

    summary = repository.get_contributor_own_summary(db, contributor.id)
    validated = summary["validated"]
    text_translations = summary["text_translations"]
    total_paid = repository.get_total_paid(db, contributor.id)
    amount_estime = estimate_amount(validated["duration_ms"], text_translations)
    amount_restant = amount_estime - total_paid

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Audio validé", format_duration(validated["duration_ms"]))
    col2.metric("Traductions texte", text_translations)
    col3.metric(f"Estimé ({CURRENCY})", round(amount_estime, 2))
    col4.metric(f"Déjà versé ({CURRENCY})", round(total_paid, 2))
    col5.metric(f"Reste dû ({CURRENCY})", round(amount_restant, 2))

    st.divider()
    st.subheader("Enregistrer un versement")
    with st.form(key=f"payment_form_{contributor.id}"):
        col_amount, col_note, col_btn = st.columns([1, 2, 1])
        payment_amount = col_amount.number_input(f"Montant ({CURRENCY})", min_value=0.0, step=100.0)
        payment_note = col_note.text_input("Note (optionnel)", placeholder="ex. Paiement août 2026")
        payment_submitted = col_btn.form_submit_button("💾 Enregistrer")

    if payment_submitted:
        if payment_amount <= 0:
            st.error("Entre un montant supérieur à 0.")
        else:
            repository.create_payment(db, contributor.id, payment_amount, currency=CURRENCY, note=payment_note or None)
            st.success("Versement enregistré.")
            st.rerun()

    payments = repository.list_payments(db, contributor.id)
    if payments:
        st.caption("Historique des versements")
        for payment in payments:
            col_p, col_del = st.columns([5, 1])
            note_part = f" — {payment.note}" if payment.note else ""
            col_p.write(f"{payment.paid_at:%d/%m/%Y %H:%M} — **{payment.amount} {payment.currency or CURRENCY}**{note_part}")
            if col_del.button("🗑️", key=f"del_payment_{payment.id}"):
                repository.delete_payment(db, payment.id)
                st.rerun()

    st.divider()
    st.subheader("Export individuel")
    only_validated_export = st.checkbox("Uniquement les enregistrements validés", value=True, key="export_only_validated")
    zip_bytes, skipped = build_dataset_zip(db, only_validated=only_validated_export, contributor_id=contributor.id)
    if skipped:
        st.warning(f"{skipped} enregistrement(s) ignoré(s) : fichier audio introuvable sur disque.")
    st.download_button(
        f"📦 Télécharger les contributions de {contributor.name} (ZIP)",
        data=zip_bytes,
        file_name=f"{contributor.code}.zip",
        mime="application/zip",
    )

    st.divider()
    st.subheader("Traductions")

    translations = repository.get_contributor_translations(db, contributor.id)
    if not translations:
        st.caption("Aucune traduction pour l'instant.")

    for translation in translations:
        sentence = translation.sentence
        moore_preview = translation.text_moore[:40] if translation.text_moore else "(audio seulement)"
        with st.expander(f"« {sentence.text_fr[:70]} » — {moore_preview}"):
            st.write(f"**FR** : {sentence.text_fr}")
            st.write(f"**Mooré** : {translation.text_moore or '_(pas de texte, audio seulement)_'}")
            if sentence.category:
                st.caption(f"Catégorie : {sentence.category}")

            if not translation.recordings:
                st.caption("Aucun audio pour cette traduction.")
            for recording in translation.recordings:
                st.caption(f"Statut : {recording.status.value} — durée {format_duration(recording.duration_ms)}")
                audio_path = recording.cleaned_path or recording.original_path
                try:
                    st.audio(storage.read_audio_file(audio_path))
                except (FileNotFoundError, TypeError):
                    st.warning("Fichier audio introuvable sur disque.")

    db.close()

# ------------------------------------------------------------------------ Liste
else:
    overview = repository.list_contributors_overview(db)
    db.close()

    search = st.text_input("Rechercher un contributeur (nom ou code)")
    if search:
        needle = search.strip().lower()
        overview = [
            o for o in overview
            if needle in o["contributor"].name.lower() or needle in o["contributor"].code.lower()
        ]

    if not overview:
        st.info("Aucun contributeur pour l'instant.")
        st.stop()

    rows = []
    for o in overview:
        validated = o["status_summary"]["validated"]
        amount_estime = estimate_amount(validated["duration_ms"], o["text_translation_count"])
        rows.append(
            {
                "Nom": o["contributor"].name,
                "Code": o["contributor"].code,
                "Traductions": o["translation_count"],
                "— dont texte": o["text_translation_count"],
                "Audio validé": format_duration(validated["duration_ms"]),
                f"Estimé ({CURRENCY})": round(amount_estime, 2),
                f"Déjà versé ({CURRENCY})": round(o["total_paid"], 2),
                f"Reste dû ({CURRENCY})": round(amount_estime - o["total_paid"], 2),
                "Dernière activité": o["last_activity"].strftime("%d/%m/%Y") if o["last_activity"] else "—",
            }
        )

    st.dataframe(rows, use_container_width=True, hide_index=True)

    st.divider()
    options = {f"{o['contributor'].name} ({o['contributor'].code})": o["contributor"].id for o in overview}
    choice = st.selectbox("Voir la fiche détaillée de…", ["—"] + list(options.keys()))
    if choice != "—" and st.button("Ouvrir la fiche"):
        st.session_state.selected_contributor_id = options[choice]
        st.rerun()
