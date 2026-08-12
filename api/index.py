import sys
from pathlib import Path

# Add the root directory to sys.path so that imdb_sentiment_classifier can be imported
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

# Add imdb_sentiment_classifier directory to sys.path to allow importing cinesense directly
imdb_dir = root_dir / "imdb_sentiment_classifier"
if str(imdb_dir) not in sys.path:
    sys.path.insert(0, str(imdb_dir))

from cinesense.api.server import app
