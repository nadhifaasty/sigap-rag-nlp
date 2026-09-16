import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

DATA_DIR = PROJECT_ROOT / "data"
KONSESI_DIR = DATA_DIR / "konsesi"
SPASIAL_DIR = DATA_DIR / "spasial"
CACHE_DIR = DATA_DIR / "_cache"
REGULASI_DIR = DATA_DIR / "regulasi"

GFW_API_BASE = "https://data-api.globalforestwatch.org"
GFW_API_KEY = os.getenv("GFW_API_KEY", "")
GFW_AUTH_TOKEN = os.getenv("GFW_AUTH_TOKEN", "")

FWI_BASE = "https://petahutan.fwi.or.id"
FWI_MAP_ID = "62e285e0-d590-481a-a45c-01b535f25402"

USER_AGENT = "sigap-hutan-rag/0.1 (+academic project)"


def ensure_dirs() -> None:
    for d in (DATA_DIR, KONSESI_DIR, SPASIAL_DIR, CACHE_DIR, REGULASI_DIR):
        d.mkdir(parents=True, exist_ok=True)