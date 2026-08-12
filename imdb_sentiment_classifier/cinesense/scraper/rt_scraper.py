import json
import re
from urllib.parse import urlparse

import cloudscraper
from bs4 import BeautifulSoup

from cinesense.config import DEFAULT_MAX_REVIEWS_PER_SOURCE
from cinesense.scraper.common import clean_text, headers, polite_sleep, slugify, unique_keep_order


def _candidate_paths(scraper, title: str, media_type: str) -> list[str]:
    prefix = "tv" if media_type == "tv" else "m"
    base_slug = slugify(title, "_")
    candidates = [
        f"/{prefix}/{base_slug}",
        f"/{prefix}/{base_slug.replace('_', '-')}",
    ]
    try:
        resp = scraper.get("https://www.rottentomatoes.com/search", params={"search": title}, headers=headers(), timeout=15)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            for a_tag in soup.select("a[href]"):
                path = urlparse(a_tag.get("href", "")).path.rstrip("/")
                if path.startswith(f"/{prefix}/"):
                    candidates.insert(0, path)
    except Exception:
        pass
    return unique_keep_order(candidates)


def _extract_ems_id(scraper, candidate_paths: list[str]) -> tuple[str, str]:
    for path in candidate_paths:
        try:
            resp = scraper.get(f"https://www.rottentomatoes.com{path}/reviews?type=user", headers=headers(), timeout=15)
            if resp.status_code != 200:
                continue
            soup = BeautifulSoup(resp.text, "html.parser")
            script_tag = soup.find("script", {"data-json": "reviewsData"})
            if script_tag and script_tag.string:
                data = json.loads(script_tag.string)
                ems_id = data.get("media", {}).get("emsId", "")
                if ems_id:
                    return ems_id, path
            match = re.search(r'"emsId"\s*:\s*"([^"]+)"', resp.text)
            if match:
                return match.group(1), path
        except Exception:
            continue
    return "", ""


def scrape(
    title: str,
    imdb_id: str,
    tmdb_id: str,
    media_type: str,
    max_reviews: int = DEFAULT_MAX_REVIEWS_PER_SOURCE,
) -> list[str]:
    del imdb_id, tmdb_id
    scraper = cloudscraper.create_scraper()
    reviews: list[str] = []
    ems_id, referer_path = _extract_ems_id(scraper, _candidate_paths(scraper, title, media_type))
    if not ems_id:
        return []

    api_kinds = ["tvSeries", "movies"] if media_type == "tv" else ["movies"]
    for api_kind in api_kinds:
        after_cursor = ""
        api_url = f"https://www.rottentomatoes.com/napi/rtcf/v1/{api_kind}/{ems_id}/reviews"
        while len(reviews) < max_reviews:
            try:
                resp = scraper.get(
                    api_url,
                    params={
                        "after": after_cursor,
                        "before": "",
                        "pageCount": min(50, max_reviews - len(reviews)),
                        "topOnly": "false",
                        "type": "audience",
                        "verified": "false",
                    },
                    headers=headers({
                        "Accept": "application/json",
                        "Referer": f"https://www.rottentomatoes.com{referer_path}/reviews",
                    }),
                    timeout=15,
                )
                if resp.status_code != 200:
                    break
                data = resp.json()
                page_reviews = data.get("reviews", [])
                if not page_reviews:
                    break
                reviews.extend(clean_text(item.get("review", "")) for item in page_reviews)
                page_info = data.get("pageInfo", {})
                if not page_info.get("hasNextPage"):
                    break
                after_cursor = page_info.get("endCursor", "")
                polite_sleep()
            except Exception:
                break
        if reviews:
            break
    return unique_keep_order(reviews)[:max_reviews]
