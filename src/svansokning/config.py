import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
CACHE_DIR = REPO_ROOT / ".cache"

LISTINGS_PARQUET = DATA_DIR / "listings.parquet"
GEOCODE_CACHE = DATA_DIR / "geocode_cache.json"
UI_STATE = DATA_DIR / "ui_state.json"

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
RESEND_TO_EMAIL = os.getenv("RESEND_TO_EMAIL", "")
RESEND_FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL", "onboarding@resend.dev")

USER_AGENT = "svansokning/0.1 (+ricardo.twumasi@gmail.com)"
