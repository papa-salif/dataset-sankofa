import os

from dotenv import load_dotenv

load_dotenv()

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "moore_dataset")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")

DATABASE_URL = (
    f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

AUDIO_ROOT = os.getenv("AUDIO_ROOT", "data/audio")
# Toujours des "/" (pas os.path.join) : ces chemins sont stockés en base et
# doivent rester lisibles aussi bien depuis Windows (dev local) que Linux
# (conteneurs) — un antislash n'est pas un séparateur de chemin sous Linux.
AUDIO_ORIGINAL_DIR = f"{AUDIO_ROOT}/original"
AUDIO_CLEANED_DIR = f"{AUDIO_ROOT}/cleaned"

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")

CURRENCY = os.getenv("CURRENCY", "FCFA")
DEFAULT_RATE_PER_MINUTE = float(os.getenv("DEFAULT_RATE_PER_MINUTE", "0"))

DEFAULT_CATEGORIES = [
    "Santé",
    "Commerce",
    "Agriculture",
    "Administration",
    "Éducation",
    "Vie quotidienne",
    "Autre",
]
