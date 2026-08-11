import streamlit as st

from src.config import ADMIN_PASSWORD

st.set_page_config(page_title="Collecte Français → Mooré", page_icon="🎙️", layout="wide")


def show_login():
    st.title("🎙️ Collecte de données Français → Mooré")
    st.write("Entre ton nom pour continuer.")

    name = st.text_input("Ton nom")
    is_admin_name = name.strip().lower() == "admin"

    password = None
    if is_admin_name:
        password = st.text_input("Mot de passe admin", type="password")

    if st.button("Continuer", disabled=not name.strip()):
        if is_admin_name:
            if not ADMIN_PASSWORD:
                st.error("Aucun ADMIN_PASSWORD n'est défini dans le fichier .env.")
            elif password == ADMIN_PASSWORD:
                st.session_state.role = "admin"
                st.rerun()
            else:
                st.error("Mot de passe incorrect.")
        else:
            st.session_state.role = "contributor"
            st.session_state.contributor_name = name.strip()
            st.rerun()

    st.stop()


if "role" not in st.session_state:
    show_login()

if st.session_state.role == "admin":
    st.session_state.setdefault("contributor_name", "Admin")
    pages = [
        st.Page("app_pages/2_Admin_Overview.py", title="Overview", icon="📊", default=True),
        st.Page("app_pages/3_Admin_Bulk_Upload.py", title="Bulk Upload", icon="📥"),
        st.Page("app_pages/4_Admin_Translation_Queue.py", title="Translation Queue", icon="📝"),
        st.Page("app_pages/5_Admin_Audio_Lab.py", title="Audio Lab", icon="🎧"),
        st.Page("app_pages/6_Admin_Export.py", title="Export", icon="📤"),
        st.Page("app_pages/1_Contributeur.py", title="Contribuer", icon="🧑"),
    ]
    identity_label = "Admin"
else:
    pages = [
        st.Page("app_pages/1_Contributeur.py", title="Contribuer", icon="🧑", default=True),
    ]
    identity_label = st.session_state.contributor_name

with st.sidebar:
    st.caption(f"Connecté comme **{identity_label}**")
    if st.button("Se déconnecter"):
        for key in ["role", "contributor_name"]:
            st.session_state.pop(key, None)
        st.rerun()

navigation = st.navigation(pages)
navigation.run()
