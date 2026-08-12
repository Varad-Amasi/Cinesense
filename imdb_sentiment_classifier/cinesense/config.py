from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("CINESENSE_DATA_DIR", BASE_DIR / "data"))
MODEL_DIR = Path(os.getenv("CINESENSE_MODEL_DIR", BASE_DIR / "models"))

TMDB_API_KEY = os.getenv("TMDB_API_KEY", "").strip()
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"

DEFAULT_MAX_REVIEWS_PER_SOURCE = int(os.getenv("CINESENSE_MAX_REVIEWS_PER_SOURCE", "1000"))
