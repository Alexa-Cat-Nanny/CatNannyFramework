from pathlib import Path
import os


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("CATNANNY_DATA_DIR", str(BASE_DIR / "data")))
UPLOAD_DIR = BASE_DIR / "uploads"
DATABASE_PATH = DATA_DIR / "catnanny.sqlite3"

DEFAULT_HOUSEHOLD_ID = "demo_household"
DEFAULT_CAT_ID = "mochi"
DEFAULT_CAT_NAME = "Mochi"

# Replace this with your deployed public URL when testing Alexa cards.
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "http://localhost:8000").rstrip("/")
