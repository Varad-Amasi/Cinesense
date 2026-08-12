import sys
import os

# Ensure nested package modules can be imported without ModuleNotFoundError
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SUBMODULE_DIR = os.path.join(ROOT_DIR, "imdb_sentiment_classifier")

for p in [ROOT_DIR, SUBMODULE_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

# Import the FastAPI app instance
try:
    from cinesense.api.server import app
except ImportError:
    from imdb_sentiment_classifier.cinesense.api.server import app  # noqa: F401
