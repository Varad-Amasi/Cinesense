import requests

from cinesense.config import DEFAULT_MAX_REVIEWS_PER_SOURCE, TMDB_API_KEY
from cinesense.scraper.common import clean_text, headers, polite_sleep, unique_keep_order

TMDB_API_BASE = "https://api.themoviedb.org/3"


def _get(path: str, params: dict | None = None) -> dict:
    if not TMDB_API_KEY:
        return {}
    merged = {"api_key": TMDB_API_KEY}
    if params:
        merged.update(params)
    resp = requests.get(f"{TMDB_API_BASE}{path}", params=merged, headers=headers(), timeout=15)
    resp.raise_for_status()
    return resp.json()


def scrape(
    title: str,
    imdb_id: str,
    tmdb_id: str,
    media_type: str,
    max_reviews: int = DEFAULT_MAX_REVIEWS_PER_SOURCE,
) -> list[str]:
    del title, imdb_id
    if not tmdb_id or not TMDB_API_KEY:
        return []
    kind = "tv" if media_type == "tv" else "movie"
    reviews: list[str] = []
    page = 1
    try:
        while len(reviews) < max_reviews:
            data = _get(f"/{kind}/{tmdb_id}/reviews", {"page": page})
            page_reviews = data.get("results", [])
            if not page_reviews:
                break
            reviews.extend(clean_text(item.get("content", "")) for item in page_reviews)
            if page >= int(data.get("total_pages") or page):
                break
            page += 1
            polite_sleep()
    except Exception:
        return unique_keep_order(reviews)[:max_reviews]
    return unique_keep_order(reviews)[:max_reviews]
