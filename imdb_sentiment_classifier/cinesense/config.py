from pathlib import Path
from dotenv import load_dotenv
import os

import tempfile

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
TMP_DIR = Path(tempfile.gettempdir())

# Serverless read-only /tmp fallbacks for Vercel / AWS Lambda
_default_data_dir = TMP_DIR / "cinesense_data" if os.getenv("VERCEL") else BASE_DIR / "data"
_default_model_dir = TMP_DIR / "cinesense_models" if os.getenv("VERCEL") else BASE_DIR / "models"

DATA_DIR = Path(os.getenv("CINESENSE_DATA_DIR", _default_data_dir))
MODEL_DIR = Path(os.getenv("CINESENSE_MODEL_DIR", _default_model_dir))

TMDB_API_KEY = os.getenv("TMDB_API_KEY", "").strip()
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"

DEFAULT_MAX_REVIEWS_PER_SOURCE = int(os.getenv("CINESENSE_MAX_REVIEWS_PER_SOURCE", "1000"))
