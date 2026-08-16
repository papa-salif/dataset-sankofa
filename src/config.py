import os

from dotenv import load_dotenv

load_dotenv()


def _get(key: str, default: str = "") -> str:
    """Lit d'abord les secrets Streamlit Cloud (st.secrets), sinon une
    variable d'environnement / le fichier .env (déploiement Docker).
    Le try/except couvre les environnements sans secrets.toml du tout
    (scripts CLI, conteneurs Docker) où st.secrets n'a rien à lire."""
    try:
        import streamlit as st

        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.getenv(key, default)


POSTGRES_HOST = _get("POSTGRES_HOST", "localhost")
POSTGRES_PORT = _get("POSTGRES_PORT", "5432")
POSTGRES_DB = _get("POSTGRES_DB", "moore_dataset")
POSTGRES_USER = _get("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = _get("POSTGRES_PASSWORD", "")
# "prefer" en local (Docker/postgres sans SSL) ; mettre "require" pour Neon
# ou tout autre fournisseur managé qui exige une connexion chiffrée.
POSTGRES_SSLMODE = _get("POSTGRES_SSLMODE", "prefer")

DATABASE_URL = (
    f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}?sslmode={POSTGRES_SSLMODE}"
)

AUDIO_KEY_PREFIX = _get("AUDIO_KEY_PREFIX", "audio")

# Stockage audio (Cloudinary, resource_type="raw" pour ne rien transformer).
# Les fichiers ne vivent plus sur le disque local : indispensable dès que
# l'app tourne sur un environnement au système de fichiers éphémère
# (ex. Streamlit Community Cloud).
CLOUDINARY_CLOUD_NAME = _get("CLOUDINARY_CLOUD_NAME", "")
CLOUDINARY_API_KEY = _get("CLOUDINARY_API_KEY", "")
CLOUDINARY_API_SECRET = _get("CLOUDINARY_API_SECRET", "")

ADMIN_PASSWORD = _get("ADMIN_PASSWORD", "")

CURRENCY = _get("CURRENCY", "FCFA")
DEFAULT_RATE_PER_MINUTE = float(_get("DEFAULT_RATE_PER_MINUTE", "0"))
# Tarif forfaitaire par traduction texte (indépendant de l'audio, qui se
# facture à la durée) — payé dès qu'un texte mooré est fourni pour une phrase.
DEFAULT_RATE_PER_TEXT_TRANSLATION = float(_get("DEFAULT_RATE_PER_TEXT_TRANSLATION", "0"))

DEFAULT_CATEGORIES = [
    "Santé",
    "Commerce",
    "Agriculture",
    "Administration",
    "Éducation",
    "Vie quotidienne",
    "Autre",
]
