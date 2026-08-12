import re
import requests

from cinesense.config import DEFAULT_MAX_REVIEWS_PER_SOURCE
from cinesense.scraper.common import clean_text, headers, polite_sleep, unique_keep_order, slugify

IMDB_GRAPHQL_URL = "https://api.graphql.imdb.com/"
IMDB_BASE = "https://www.imdb.com"

REVIEWS_QUERY = """
query Reviews($titleId: ID!, $first: Int!, $after: ID) {
  title(id: $titleId) {
    reviews(first: $first, after: $after) {
      pageInfo { hasNextPage endCursor }
      edges { node { text { originalText { plainText } } } }
    }
  }
}
"""


def find_imdb_id(title: str, media_type: str = "movie") -> str:
    safe_query = slugify(title, "_")
    url = f"https://v3.sg.media-imdb.com/suggestion/x/{safe_query}.json"
    allowed = {"tvSeries", "tvMiniSeries"} if media_type == "tv" else {"movie", "tvMovie", "short", "video"}
    try:
        resp = requests.get(url, headers=headers(), timeout=10)
        resp.raise_for_status()
        for item in resp.json().get("d", []):
            if item.get("qid") not in allowed:
                continue
            imdb_id = item.get("id", "")
            if imdb_id.startswith("tt"):
                return imdb_id
    except Exception:
        return ""
    return ""


def _scrape_graphql(imdb_id: str, max_reviews: int) -> list[str]:
    reviews: list[str] = []
    after_cursor = None

    while len(reviews) < max_reviews:
        batch_size = min(50, max_reviews - len(reviews))
        variables = {"titleId": imdb_id, "first": batch_size}
        if after_cursor:
            variables["after"] = after_cursor

        resp = requests.post(
            IMDB_GRAPHQL_URL,
            json={"query": REVIEWS_QUERY, "variables": variables},
            headers=headers({"Content-Type": "application/json"}),
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        reviews_data = data.get("data", {}).get("title", {})
        if reviews_data is None:
            break
        reviews_data = reviews_data.get("reviews", {})
        edges = reviews_data.get("edges", []) if reviews_data else []
        if not edges:
            break

        for edge in edges:
            plain = edge.get("node", {}).get("text", {}).get("originalText", {}).get("plainText", "")
            text = clean_text(plain)
            if len(text) > 30:
                reviews.append(text)

        page_info = reviews_data.get("pageInfo", {})
        if not page_info.get("hasNextPage"):
            break
        after_cursor = page_info.get("endCursor")
        polite_sleep()

    return unique_keep_order(reviews)


def _scrape_html(imdb_id: str, max_reviews: int) -> list[str]:
    from bs4 import BeautifulSoup

    resp = requests.get(f"{IMDB_BASE}/title/{imdb_id}/reviews", headers=headers(), timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    reviews: list[str] = []
    selectors = [
        "div.review-container div.text.show-more__control",
        "[data-testid='review-overflow']",
        "[data-testid='reviewContent']",
        "div.ipc-html-content-inner-div",
        "div.ipc-html-content div",
    ]
    for selector in selectors:
        blocks = soup.select(selector)
        if blocks:
            reviews.extend(clean_text(block.get_text()) for block in blocks[:max_reviews])
            break
    if not reviews:
        for div in soup.find_all("div"):
            text = clean_text(div.get_text())
            if 100 < len(text) < 5000 and not div.find("div"):
                reviews.append(text)
            if len(reviews) >= max_reviews:
                break
    return unique_keep_order(reviews)[:max_reviews]


def scrape(
    title: str,
    imdb_id: str,
    tmdb_id: str,
    media_type: str,
    max_reviews: int = DEFAULT_MAX_REVIEWS_PER_SOURCE,
) -> list[str]:
    del tmdb_id
    imdb_id = imdb_id or find_imdb_id(title, "tv" if media_type == "tv" else "movie")
    if not imdb_id:
        return []
    try:
        reviews = _scrape_graphql(imdb_id, max_reviews)
    except Exception:
        reviews = []
    if not reviews:
        try:
            reviews = _scrape_html(imdb_id, max_reviews)
        except Exception:
            reviews = []
    return unique_keep_order(reviews)[:max_reviews]
