import streamlit as st

from src import admin_tokens, repository
from src.config import ADMIN_PASSWORD
from src.db import SessionLocal

st.set_page_config(page_title="Collecte Français → Mooré", page_icon="🎙️", layout="wide")


def restore_session_from_url():
    """Reconstitue la session à partir des paramètres d'URL, pour qu'un
    rafraîchissement de page (F5) ne déconnecte pas l'utilisateur."""
    token = st.query_params.get("admin_token")
    if token and admin_tokens.is_valid(token):
        st.session_state.role = "admin"
        st.session_state.admin_token = token
        return

    code = st.query_params.get("code")
    if code:
        db = SessionLocal()
        contributor = repository.get_contributor_by_code(db, code)
        db.close()
        if contributor:
            st.session_state.role = "contributor"
            st.session_state.contributor_id = contributor.id
            st.session_state.contributor_name = contributor.name
            st.session_state.contributor_code = contributor.code


def _login_contributor(contributor):
    st.session_state.role = "contributor"
    st.session_state.contributor_id = contributor.id
    st.session_state.contributor_name = contributor.name
    st.session_state.contributor_code = contributor.code
    st.query_params["code"] = contributor.code
    for key in ["login_step", "pending_name"]:
        st.session_state.pop(key, None)


def _go_to_step(step):
    st.session_state.login_step = step
    st.rerun()


def show_login():
    st.title("🎙️ Collecte de données Français → Mooré")

    step = st.session_state.get("login_step", "name")

    if step == "name":
        st.write("Entre ton nom pour continuer.")
        name = st.text_input("Ton nom")
        if st.button("Continuer", disabled=not name.strip()):
            st.session_state.pending_name = name.strip()
            if name.strip().lower() == "admin":
                _go_to_step("admin_password")
            else:
                _go_to_step("contributor_next")

    elif step == "admin_password":
        st.write(f"Bonjour **{st.session_state.pending_name}**, entre le mot de passe admin.")
        password = st.text_input("Mot de passe admin", type="password")
        col_back, col_go = st.columns([1, 3])
        if col_back.button("← Retour"):
            _go_to_step("name")
        if col_go.button("Continuer", disabled=not password):
            if not ADMIN_PASSWORD:
                st.error("Aucun ADMIN_PASSWORD n'est défini dans le fichier .env.")
            elif password == ADMIN_PASSWORD:
                token = admin_tokens.issue_token()
                st.session_state.role = "admin"
                st.session_state.admin_token = token
                st.query_params["admin_token"] = token
                for key in ["login_step", "pending_name"]:
                    st.session_state.pop(key, None)
                st.rerun()
            else:
                st.error("Mot de passe incorrect.")

    elif step == "contributor_next":
        name = st.session_state.pending_name
        st.write(f"Bonjour **{name}** !")

        code = st.text_input("As-tu déjà un code ? Entre-le ici (sinon laisse vide).", placeholder="CTR-XXXX")
        if st.button("Valider mon code", disabled=not code.strip()):
            db = SessionLocal()
            contributor = repository.get_contributor_by_code(db, code)
            db.close()
            if contributor:
                _login_contributor(contributor)
                st.rerun()
            else:
                st.error("Ce code n'existe pas.")

        st.divider()
        col_create, col_recover, col_back = st.columns(3)
        if col_create.button("Je n'ai pas de code"):
            db = SessionLocal()
            contributor = repository.create_contributor(db, name)
            db.close()
            st.session_state.just_created_code = contributor.code
            _login_contributor(contributor)
            st.rerun()
        if col_recover.button("Je l'ai oublié"):
            _go_to_step("recover")
        if col_back.button("← Retour"):
            _go_to_step("name")

    elif step == "recover":
        name = st.session_state.pending_name
        db = SessionLocal()
        matches = repository.find_contributors_by_name(db, name)
        db.close()

        if not matches:
            st.warning(f"Aucun compte trouvé avec le nom « {name} ».")
        elif len(matches) == 1:
            contributor = matches[0]
            st.success(f"Compte retrouvé ! Ton code est **{contributor.code}** — note-le pour la prochaine fois.")
            if st.button("Continuer"):
                _login_contributor(contributor)
                st.rerun()
        else:
            st.write(f"Plusieurs comptes portent le nom « {name} ». Choisis le tien :")
            for i, contributor in enumerate(matches, start=1):
                label = f"Compte {i} (créé le {contributor.created_at:%d/%m/%Y})"
                if st.button(label, key=f"recover_{contributor.id}"):
                    _login_contributor(contributor)
                    st.rerun()

        if st.button("← Retour"):
            _go_to_step("name")

    st.stop()


if "role" not in st.session_state:
    restore_session_from_url()

if "role" not in st.session_state:
    show_login()

if st.session_state.role == "admin":
    if "contributor_id" not in st.session_state:
        db = SessionLocal()
        admin_contributor = repository.get_or_create_admin_contributor(db)
        db.close()
        st.session_state.contributor_id = admin_contributor.id
        st.session_state.contributor_name = admin_contributor.name
        st.session_state.contributor_code = admin_contributor.code
    pages = [
        st.Page("app_pages/2_Admin_Overview.py", title="Overview", icon="📊", default=True),
        st.Page("app_pages/3_Admin_Bulk_Upload.py", title="Bulk Upload", icon="📥"),
        st.Page("app_pages/4_Admin_Translation_Queue.py", title="Translation Queue", icon="📝"),
        st.Page("app_pages/5_Admin_Audio_Lab.py", title="Audio Lab", icon="🎧"),
        st.Page("app_pages/6_Admin_Export.py", title="Export", icon="📤"),
        st.Page("app_pages/7_Admin_Paiements.py", title="Paiements", icon="💰"),
        st.Page("app_pages/8_Admin_Gestion.py", title="Gestion", icon="🗂️"),
        st.Page("app_pages/1_Contributeur.py", title="Contribuer", icon="🧑"),
        st.Page("app_pages/1_Contributeur_Gains.py", title="Mes gains", icon="💵"),
    ]
    identity_label = "Admin"
else:
    pages = [
        st.Page("app_pages/1_Contributeur.py", title="Contribuer", icon="🧑", default=True),
        st.Page("app_pages/1_Contributeur_Gains.py", title="Mes gains", icon="💵"),
    ]
    identity_label = st.session_state.contributor_name

with st.sidebar:
    just_created_code = st.session_state.pop("just_created_code", None)
    if just_created_code:
        st.success(f"Ton code est **{just_created_code}** — note-le pour te reconnecter.")
    st.caption(f"Connecté comme **{identity_label}**")
    if st.session_state.role == "contributor":
        st.caption(f"Ton code : `{st.session_state.contributor_code}` (note-le pour te reconnecter)")
    if st.button("Se déconnecter"):
        if st.session_state.get("role") == "admin":
            admin_tokens.revoke(st.session_state.get("admin_token"))
        st.query_params.clear()
        for key in ["role", "contributor_name", "contributor_id", "contributor_code", "admin_token"]:
            st.session_state.pop(key, None)
        st.rerun()

navigation = st.navigation(pages)
navigation.run()
