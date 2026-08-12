import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Callable

from cinesense.config import DEFAULT_MAX_REVIEWS_PER_SOURCE
from cinesense.scraper import imdb_scraper, letterboxd_scraper, rt_scraper, serializd_scraper, tmdb_scraper
from cinesense.scraper.common import unique_keep_order


@dataclass
class ReviewItem:
    text: str
    source: str


Scraper = Callable[[str, str, str, str, int], list[str]]


def _sources_for(media_type: str) -> dict[str, Scraper]:
    sources: dict[str, Scraper] = {
        "imdb": imdb_scraper.scrape,
        "rotten_tomatoes": rt_scraper.scrape,
        "tmdb": tmdb_scraper.scrape,
    }
    if media_type == "tv":
        sources["letterboxd"] = lambda *args, **kwargs: []
        sources["serializd"] = serializd_scraper.scrape
    else:
        sources["letterboxd"] = letterboxd_scraper.scrape
        sources["serializd"] = lambda *args, **kwargs: []
    return sources


async def aggregate_reviews(
    title: str,
    imdb_id: str = "",
    tmdb_id: str = "",
    media_type: str = "movie",
    max_reviews_per_source: int = DEFAULT_MAX_REVIEWS_PER_SOURCE,
) -> dict[str, list[str]]:
    loop = asyncio.get_running_loop()
    sources = _sources_for(media_type)
    results: dict[str, list[str]] = {}

    def run_source(name: str, scraper: Scraper) -> tuple[str, list[str]]:
        try:
            reviews = scraper(title, imdb_id, tmdb_id, media_type, max_reviews_per_source)
        except Exception:
            reviews = []
        return name, unique_keep_order(reviews)[:max_reviews_per_source]

    with ThreadPoolExecutor(max_workers=len(sources)) as executor:
        tasks = [
            loop.run_in_executor(executor, run_source, name, scraper)
            for name, scraper in sources.items()
        ]
        for name, reviews in await asyncio.gather(*tasks):
            results[name] = reviews
    return results


def flatten_sources(source_reviews: dict[str, list[str]]) -> list[ReviewItem]:
    seen: set[str] = set()
    items: list[ReviewItem] = []
    for source, reviews in source_reviews.items():
        for review in reviews:
            if review not in seen:
                seen.add(review)
                items.append(ReviewItem(text=review, source=source))
    return items


async def aggregate_all_reviews(
    imdb_id: str,
    title: str,
    year: str = "",
    is_series: bool = False,
    max_total: int = DEFAULT_MAX_REVIEWS_PER_SOURCE,
) -> dict[str, list[str]]:
    del year
    return await aggregate_reviews(title, imdb_id=imdb_id, media_type="tv" if is_series else "movie", max_reviews_per_source=max_total)
