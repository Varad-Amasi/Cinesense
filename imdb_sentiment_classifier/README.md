# CineSense

CineSense is a sentiment-analysis toolkit for movie and TV titles. It resolves a title, collects audience-written reviews from multiple sources, and classifies the overall reaction with a trained text model.

It is designed for:

- quick local experiments,
- interactive CLI lookups,
- a small FastAPI service,
- and extending or swapping review sources over time.

## What It Uses

- Title resolution through TMDB, with an IMDb fallback when TMDB is unavailable.
- Review aggregation from IMDb, Rotten Tomatoes, Letterboxd, TMDB, and Serializd.
- Sentiment classification with TF-IDF plus Logistic Regression by default.
- Optional training/runtime backends that can use PyTorch or XGBoost when available.

## Source Routing

The scraper set is not identical for movies and series:

- Movies can use IMDb, Rotten Tomatoes, Letterboxd, and TMDB.
- Series can use IMDb, Rotten Tomatoes, TMDB, and Serializd.
- Letterboxd is movie-only.
- Serializd is series-only.

This is intentional and is handled in the aggregator, not by the UI.

## Project Layout

```text
imdb_sentiment_classifier/
  main.py                       # CLI entrypoint
  imdb_sentiment_classifier.py  # Compatibility wrapper
  cinesense/
    api/server.py               # FastAPI app
    main.py                     # CLI flow
    ml/
      classifier.py
      train.py
    scraper/
      imdb_scraper.py
      rt_scraper.py
      letterboxd_scraper.py
      tmdb_scraper.py
      serializd_scraper.py
    utils/
      aggregator.py
      title_resolver.py
  static/
    index.html
    script.js
    style.css
  scripts/
    dump_lb.py
  test_*.py
  data/
  models/
```

## Requirements

Python 3.9 or newer is recommended.

The main runtime dependencies are:

- requests
- beautifulsoup4
- nltk
- scikit-learn
- cloudscraper
- fastapi
- uvicorn
- playwright
- torch
- xgboost

See [requirements.txt](requirements.txt) for the full pinned list.

## Setup

Windows PowerShell example:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m playwright install chromium
```

Notes:

- `playwright` is required for sites that depend on a real browser.
- Some scrapers use `cloudscraper` to reduce blocking on protected pages.
- The first training run may download the Stanford ACL IMDB corpus.

## Configuration

Create a `.env` file in the project root if you want TMDB-backed title lookup.

```dotenv
TMDB_API_KEY=your_tmdb_api_key_here
```

Optional environment settings:

- `PLAYWRIGHT_BROWSERS_PATH` for a custom browser install location.

If `TMDB_API_KEY` is missing, search falls back to IMDb suggestions.

## Run The CLI

Start the interactive terminal app:

```bash
python main.py
```

The CLI flow is:

1. enter a title,
2. choose movie / series / auto,
3. pick a result from the search list,
4. wait while reviews are scraped and classified.

For compatibility, `imdb_sentiment_classifier.py` still points to the same CLI.

## Run The API

Start the FastAPI server with Uvicorn:

```bash
python -m uvicorn cinesense.api.server:app --host 127.0.0.1 --port 8000 --log-level info
```

### Endpoints

- `GET /` serves the static web UI.
- `GET /status` returns model readiness and backend name.
- `GET /api/status` mirrors `/status`.
- `POST /search` returns title matches.
- `POST /api/search` returns title matches as JSON objects.
- `POST /classify` classifies a title using the typed request model.
- `POST /api/classify` classifies a title from a raw JSON body.

### Search Request

```json
{
  "query": "Breaking Bad",
  "type": "series"
}
```

### Classify Request

```json
{
  "title": "Breaking Bad",
  "type": "series",
  "max_reviews": 1000
}
```

`max_reviews` is clamped to the range 1 to 5000.

### Classify Response

The response includes:

- title metadata,
- verdict and confidence,
- total review counts,
- per-source review counts,
- positive / negative counts,
- sample reviews,
- and the resolved TMDB / IMDb identifiers.

## How Title Resolution Works

The resolver tries TMDB first, then IMDb fallback search if needed.

Returned metadata includes:

- `title`
- `year`
- `media_type`
- `tmdb_id`
- `imdb_id`
- `poster_url`
- `overview`
- `genres`

That metadata is then passed into the review aggregators.

## Review Aggregation

The aggregator collects reviews from each applicable source, deduplicates them, and truncates the results per source.

Source behavior in practice:

- IMDb tries GraphQL first and falls back to the HTML reviews page.
- Rotten Tomatoes resolves the media page and then reads the audience review API.
- Letterboxd resolves a movie page from IMDb and reads review pages.
- TMDB and Serializd are used for their respective media types.

If a source fails or returns no reviews, the rest of the pipeline continues.

## Training And Backends

The default training pipeline uses:

- TF-IDF vectorization,
- Logistic Regression,
- class-balanced weights,
- and cached preprocessing artifacts.

The code will attempt higher-performance backends when available and fall back cleanly.

Training data comes from:

- Stanford ACL IMDB sentiment corpus,
- NLTK `movie_reviews`.

Run training manually with:

```bash
python -m cinesense.ml.train --output models/tfidf_logreg.joblib
```

## Tests

Run the test suite with:

```bash
pytest -q
```

Some scraper-related tests may require network access.

## Troubleshooting

- If the API says the model is still training, wait for startup to finish and check `/api/status`.
- If search returns no results, verify `TMDB_API_KEY` or rely on the IMDb fallback.
- If a movie returns no Letterboxd reviews, the page may not resolve cleanly or Letterboxd may have blocked the request.
- If a TV title does not include Letterboxd, that is expected.
- If Playwright-based scraping fails, make sure Chromium is installed with `python -m playwright install chromium`.

## Development Notes

- `cinesense/utils/aggregator.py` controls which sources are active for each media type.
- `cinesense/utils/title_resolver.py` handles TMDB search and IMDb fallback logic.
- `cinesense/api/server.py` contains the FastAPI endpoints and response schema.
- `cinesense/main.py` contains the CLI workflow.

## License And Credits

This project uses public review sources and public datasets. Check the terms for TMDB, IMDb, Rotten Tomatoes, Letterboxd, Stanford ACL IMDB, and NLTK before redistributing data or derived artifacts.
