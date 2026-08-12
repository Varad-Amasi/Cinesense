import cloudscraper
from bs4 import BeautifulSoup

from cinesense.config import DEFAULT_MAX_REVIEWS_PER_SOURCE
from cinesense.scraper.imdb_scraper import find_imdb_id
from cinesense.scraper.common import clean_text, headers, polite_sleep, unique_keep_order


def scrape(
    title: str,
    imdb_id: str,
    tmdb_id: str,
    media_type: str,
    max_reviews: int = DEFAULT_MAX_REVIEWS_PER_SOURCE,
) -> list[str]:
    del tmdb_id  # title is still needed for find_imdb_id fallback
    if media_type == "tv":
        return []

    imdb_id = imdb_id or find_imdb_id(title, "movie")
    if not imdb_id:
        return []

    scraper = cloudscraper.create_scraper()
    reviews: list[str] = []
    try:
        resp = scraper.get(f"https://letterboxd.com/imdb/{imdb_id}", headers=headers(), allow_redirects=True, timeout=15)
        if resp.status_code != 200:
            return []
        film_url = resp.url if resp.url.endswith("/") else resp.url + "/"
        page = 1
        while len(reviews) < max_reviews:
            page_resp = scraper.get(f"{film_url}reviews/by/activity/page/{page}/", headers=headers(), timeout=15)
            if page_resp.status_code != 200:
                break
            soup = BeautifulSoup(page_resp.text, "html.parser")
            blocks = soup.select(".body-text")
            if not blocks:
                break
            reviews.extend(clean_text(block.get_text()) for block in blocks)
            if not soup.select_one("a.next"):
                break
            page += 1
            polite_sleep()
    except Exception:
        return unique_keep_order(reviews)[:max_reviews]
    return unique_keep_order(reviews)[:max_reviews]
