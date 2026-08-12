from dataclasses import dataclass, asdict
import re

import requests

from cinesense.config import TMDB_API_KEY, TMDB_IMAGE_BASE
from cinesense.scraper.common import headers, slugify

TMDB_API_BASE = "https://api.themoviedb.org/3"


@dataclass
class TitleMetadata:
    title: str
    year: str
    media_type: str
    tmdb_id: str = ""
    imdb_id: str = ""
    poster_url: str = ""
    overview: str = ""
    genres: list[str] | None = None

    def to_dict(self) -> dict:
        data = asdict(self)
        data["genres"] = data["genres"] or []
        return data


def _tmdb_get(path: str, params: dict | None = None) -> dict:
    if not TMDB_API_KEY:
        return {}
    merged = {"api_key": TMDB_API_KEY}
    if params:
        merged.update(params)
    resp = requests.get(f"{TMDB_API_BASE}{path}", params=merged, headers=headers(), timeout=15)
    resp.raise_for_status()
    return resp.json()


def _year_from_date(date_value: str) -> str:
    match = re.match(r"(\d{4})", date_value or "")
    return match.group(1) if match else ""


def _details_from_tmdb(item: dict) -> TitleMetadata:
    media_type = item.get("media_type")
    tmdb_id = str(item.get("id", ""))
    kind = "tv" if media_type == "tv" else "movie"
    details = _tmdb_get(f"/{kind}/{tmdb_id}", {"append_to_response": "external_ids"})
    title = details.get("title") or details.get("name") or item.get("title") or item.get("name") or ""
    year = _year_from_date(details.get("release_date") or details.get("first_air_date") or "")
    poster_path = details.get("poster_path") or item.get("poster_path") or ""
    imdb_id = details.get("imdb_id") or details.get("external_ids", {}).get("imdb_id") or ""
    return TitleMetadata(
        title=title,
        year=year,
        media_type=kind,
        tmdb_id=tmdb_id,
        imdb_id=imdb_id or "",
        poster_url=f"{TMDB_IMAGE_BASE}{poster_path}" if poster_path else "",
        overview=details.get("overview") or item.get("overview") or "",
        genres=[genre.get("name", "") for genre in details.get("genres", []) if genre.get("name")],
    )


def search_tmdb(query: str, requested_type: str | None = None, limit: int = 8) -> list[TitleMetadata]:
    if not TMDB_API_KEY:
        return []
    requested = "tv" if requested_type in {"tv", "series"} else "movie" if requested_type == "movie" else None
    data = _tmdb_get("/search/multi", {"query": query, "include_adult": "false"})
    results: list[TitleMetadata] = []
    for item in data.get("results", []):
        if item.get("media_type") not in {"movie", "tv"}:
            continue
        if requested and item.get("media_type") != requested:
            continue
        try:
            results.append(_details_from_tmdb(item))
        except Exception:
            continue
        if len(results) >= limit:
            break
    return results


def search_imdb_fallback(query: str, requested_type: str | None = None, limit: int = 8) -> list[TitleMetadata]:
    safe_query = slugify(query, "_")
    url = f"https://v3.sg.media-imdb.com/suggestion/x/{safe_query}.json"
    requested = "tv" if requested_type in {"tv", "series"} else "movie" if requested_type == "movie" else None
    out: list[TitleMetadata] = []
    try:
        resp = requests.get(url, headers=headers(), timeout=10)
        resp.raise_for_status()
        for item in resp.json().get("d", []):
            qid = item.get("qid", "")
            media_type = "tv" if qid in {"tvSeries", "tvMiniSeries"} else "movie"
            if qid not in {"movie", "tvMovie", "tvSeries", "tvMiniSeries", "short", "video"}:
                continue
            if requested and media_type != requested:
                continue
            imdb_id = item.get("id", "")
            if not imdb_id.startswith("tt"):
                continue
            image_url = item.get("i", {}).get("imageUrl", "")
            poster_url = re.sub(r"\._V1_.*$", "._V1_QL75_UX500_.jpg", image_url) if image_url else ""
            out.append(TitleMetadata(
                title=item.get("l", "Unknown"),
                year=str(item.get("y", "")),
                media_type=media_type,
                imdb_id=imdb_id,
                poster_url=poster_url,
                genres=[],
            ))
            if len(out) >= limit:
                break
    except Exception:
        return out
    return out


def search_titles(query: str, requested_type: str | None = None, limit: int = 8) -> list[TitleMetadata]:
    return search_tmdb(query, requested_type, limit) or search_imdb_fallback(query, requested_type, limit)


def resolve_title(query: str, requested_type: str | None = None) -> TitleMetadata:
    results = search_titles(query, requested_type, limit=1)
    if results:
        return results[0]
    media_type = "tv" if requested_type in {"tv", "series"} else "movie"
    return TitleMetadata(title=query, year="", media_type=media_type, genres=[])
