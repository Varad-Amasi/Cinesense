import asyncio
import os
import sys
from pathlib import Path
import threading

# Ensure package root is in sys.path for Vercel Serverless Functions
_pkg_root = Path(__file__).resolve().parent.parent.parent
if str(_pkg_root) not in sys.path:
    sys.path.insert(0, str(_pkg_root))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from cinesense.ml.classifier import classify_reviews, verdict_for
from cinesense.ml.train import build_pipeline, load_saved_pipeline
from cinesense.utils.aggregator import aggregate_reviews, flatten_sources
from cinesense.utils.title_resolver import TitleMetadata, resolve_title, search_titles

app = FastAPI(title="cinesense-api", version="2.0.0")

# ── CORS Configuration ────────────────────────────────────────────────────
_cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_static_dir = _pkg_root / "static"
if _static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")
elif Path("static").exists():
    app.mount("/static", StaticFiles(directory="static"), name="static")

pipeline = None
model_is_ready = False
backend_name = "initializing"

VERDICT_EMOJI = {
    "WATCH": "🎬",
    "WORTH WATCHING": "👍",
    "MIXED": "🤔",
    "SKIP": "👎",
    "HARD SKIP": "⛔",
}


class ClassifyRequest(BaseModel):
    title: str
    type: str | None = None
    max_reviews: int = 1000


class SearchRequest(BaseModel):
    query: str
    type: str | None = None


def _train_model() -> None:
    global pipeline, model_is_ready, backend_name
    pipeline = build_pipeline()
    backend_name = getattr(pipeline, "training_backend_", "unknown")
    model_is_ready = True
    print("Model ready. FastAPI /classify is accepting requests.")


@app.on_event("startup")
def startup() -> None:
    # If a saved pipeline exists, load it to avoid retraining on every start.
    global pipeline, model_is_ready, backend_name
    saved = load_saved_pipeline()
    if saved is not None:
        pipeline = saved
        backend_name = getattr(pipeline, "training_backend_", "unknown")
        model_is_ready = True
        print("Loaded saved pipeline; model ready.")
        return

    if os.getenv("VERCEL"):
        print("Running on Vercel: skipping background training thread. Model must be pre-trained.")
        return

    threading.Thread(target=_train_model, daemon=True).start()


@app.get("/")
def root():
    html_path = _pkg_root / "static" / "index.html"
    if html_path.exists():
        return FileResponse(str(html_path))
    return FileResponse("static/index.html")


@app.get("/status")
def status() -> dict:
    return {"ready": model_is_ready, "backend": backend_name}


@app.get("/api/status")
def api_status() -> dict:
    return status()


@app.get("/api/firebase-config")
def firebase_config() -> dict:
    return {
        "apiKey": os.getenv("CINESENSE_FIREBASE_API_KEY") or os.getenv("VITE_FIREBASE_API_KEY") or os.getenv("FIREBASE_API_KEY", ""),
        "authDomain": os.getenv("CINESENSE_FIREBASE_AUTH_DOMAIN") or os.getenv("VITE_FIREBASE_AUTH_DOMAIN") or os.getenv("FIREBASE_AUTH_DOMAIN", ""),
        "projectId": os.getenv("CINESENSE_FIREBASE_PROJECT_ID") or os.getenv("VITE_FIREBASE_PROJECT_ID") or os.getenv("FIREBASE_PROJECT_ID", ""),
        "storageBucket": os.getenv("CINESENSE_FIREBASE_STORAGE_BUCKET") or os.getenv("VITE_FIREBASE_STORAGE_BUCKET") or os.getenv("FIREBASE_STORAGE_BUCKET", ""),
        "messagingSenderId": os.getenv("CINESENSE_FIREBASE_MESSAGING_SENDER_ID") or os.getenv("VITE_FIREBASE_MESSAGING_SENDER_ID") or os.getenv("FIREBASE_MESSAGING_SENDER_ID", ""),
        "appId": os.getenv("CINESENSE_FIREBASE_APP_ID") or os.getenv("VITE_FIREBASE_APP_ID") or os.getenv("FIREBASE_APP_ID", ""),
    }


@app.post("/search")
def search(req: SearchRequest) -> dict:
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="query is required")
    return {"results": [item.to_dict() for item in search_titles(req.query, req.type)]}


@app.post("/api/search")
def api_search(body: dict) -> dict:
    query = (body.get("query") or "").strip()
    requested_type = body.get("type")
    if not query:
        raise HTTPException(status_code=400, detail="query is required")

    results = []
    for item in search_titles(query, requested_type, limit=5):
        results.append({
            "title": item.title,
            "year": item.year,
            "poster_url": item.poster_url,
            "imdb_id": item.imdb_id,
            "tmdb_id": item.tmdb_id,
            "media_type": item.media_type,
        })
    return {"results": results}


def _metadata_from_body(body: dict) -> TitleMetadata:
    title = (body.get("title") or body.get("movie_title") or "").strip()
    requested_type = body.get("type") or body.get("media_type")
    if not title:
        raise HTTPException(status_code=400, detail="title is required")

    media_type = body.get("media_type") or ("tv" if requested_type == "series" else requested_type)
    if media_type not in {"movie", "tv"}:
        media_type = ""

    if body.get("imdb_id") or body.get("tmdb_id"):
        return TitleMetadata(
            title=title,
            year=str(body.get("year") or ""),
            media_type=media_type or "movie",
            tmdb_id=str(body.get("tmdb_id") or ""),
            imdb_id=str(body.get("imdb_id") or ""),
            poster_url=body.get("poster_url") or "",
            overview=body.get("overview") or "",
            genres=body.get("genres") or [],
        )

    return resolve_title(title, requested_type)


def _classify_metadata(meta: TitleMetadata, max_reviews: int) -> tuple[dict, list[dict], int, int, float]:
    if not model_is_ready or pipeline is None:
        raise HTTPException(status_code=503, detail="Model is still training. Please wait.")

    media_type = meta.media_type
    try:
        source_reviews = asyncio.run(
            aggregate_reviews(
                meta.title,
                imdb_id=meta.imdb_id,
                tmdb_id=meta.tmdb_id,
                media_type=media_type,
                max_reviews_per_source=max_reviews,
            )
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to scrape reviews: {exc}") from exc

    review_items = flatten_sources(source_reviews)
    if not review_items:
        raise HTTPException(status_code=404, detail="No written reviews found for this title.")

    classified = classify_reviews(pipeline, [item.text for item in review_items])
    for row, item in zip(classified, review_items):
        row["source"] = item.source

    positive_count = sum(1 for row in classified if row["sentiment"] == "Positive")
    negative_count = len(classified) - positive_count
    avg_positive = sum(row["prob_pos"] for row in classified) / len(classified)
    return source_reviews, classified, positive_count, negative_count, avg_positive


@app.post("/classify")
def classify(req: ClassifyRequest) -> dict:
    if not req.title.strip():
        raise HTTPException(status_code=400, detail="title is required")

    max_reviews = min(max(req.max_reviews, 1), 5000)
    meta = resolve_title(req.title, req.type)
    source_reviews, classified, positive_count, negative_count, avg_positive = _classify_metadata(meta, max_reviews)
    samples = sorted(classified, key=lambda row: row["confidence"], reverse=True)[:10]
    media_type = meta.media_type

    return {
        "title": meta.title,
        "type": "series" if media_type == "tv" else "movie",
        "poster_url": meta.poster_url,
        "verdict": verdict_for(avg_positive),
        "confidence": round(avg_positive * 100),
        "avg_positive_prob": round(avg_positive, 4),
        "total_reviews_analysed": len(classified),
        "source_breakdown": {source: len(reviews) for source, reviews in source_reviews.items()},
        "positive_count": positive_count,
        "negative_count": negative_count,
        "sample_reviews": [
            {
                "text": row["text"][:240],
                "source": row["source"],
                "sentiment": row["sentiment"],
                "confidence": round(row["confidence"] * 100),
            }
            for row in samples
        ],
        "metadata": {
            "year": meta.year,
            "tmdb_id": meta.tmdb_id,
            "imdb_id": meta.imdb_id,
            "overview": meta.overview,
            "genres": meta.genres or [],
        },
    }


@app.post("/api/classify")
def api_classify(body: dict) -> dict:
    max_reviews = min(max(int(body.get("max_reviews") or 1000), 1), 5000)
    meta = _metadata_from_body(body)
    source_reviews, classified, positive_count, negative_count, avg_positive = _classify_metadata(meta, max_reviews)
    verdict = verdict_for(avg_positive)
    samples = sorted(classified, key=lambda row: row["confidence"], reverse=True)[:10]

    return {
        "movie_title": meta.title,
        "year": meta.year,
        "poster_url": meta.poster_url,
        "verdict": verdict,
        "verdict_emoji": VERDICT_EMOJI[verdict],
        "confidence": round(avg_positive * 100),
        "positive_count": positive_count,
        "negative_count": negative_count,
        "total_reviews": len(classified),
        "source_counts": {source: len(reviews) for source, reviews in source_reviews.items()},
        "sample_reviews": [
            {
                "text": row["text"][:240],
                "label": row["sentiment"],
                "confidence": round(row["confidence"] * 100),
            }
            for row in samples
        ],
    }
