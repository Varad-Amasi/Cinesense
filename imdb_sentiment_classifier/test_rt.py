import asyncio
import re
import json
import cloudscraper
from bs4 import BeautifulSoup

def _clean_text(text):
    import re
    return re.sub(r"\s+", " ", text).strip()

def _scrape_rt():
    scraper = cloudscraper.create_scraper()
    reviews = []
    title = "Dune"
    is_series = False
    max_reviews = 50

    slug = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")
    prefix = "tv" if is_series else "m"

    ems_id = None
    for candidate_slug in [slug, slug.replace("_", "-")]:
        page_url = f"https://www.rottentomatoes.com/{prefix}/{candidate_slug}/reviews?type=user"
        print(f"Trying: {page_url}")
        try:
            resp = scraper.get(page_url, timeout=15)
            print(f"  Status: {resp.status_code}")
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                script_tag = soup.find("script", {"data-json": "reviewsData"})
                print(f"  Script found: {script_tag is not None}")
                if script_tag:
                    data = json.loads(script_tag.string)
                    ems_id = data.get("media", {}).get("emsId")
                    print(f"  emsId: {ems_id}")
                    slug = candidate_slug
                    break
        except Exception as e:
            print(f"  Exception: {e}")
            continue

    if not ems_id:
        print("No emsId found! Returning empty.")
        return []

    api_url = f"https://www.rottentomatoes.com/napi/rtcf/v1/movies/{ems_id}/reviews"
    after_cursor = ""
    while len(reviews) < max_reviews:
        try:
            resp = scraper.get(
                api_url,
                params={"after": after_cursor, "before": "", "pageCount": 20, "topOnly": "false", "type": "audience", "verified": "false"},
                headers={"Accept": "application/json", "Referer": f"https://www.rottentomatoes.com/{prefix}/{slug}/reviews"},
                timeout=15,
            )
            print(f"API status: {resp.status_code}")
            data = resp.json()
            page_reviews = data.get("reviews", [])
            print(f"Page reviews: {len(page_reviews)}")
            if not page_reviews:
                break
            for r in page_reviews:
                text = _clean_text(r.get("review", ""))
                if len(text) > 30:
                    reviews.append(text)
            page_info = data.get("pageInfo", {})
            if not page_info.get("hasNextPage"):
                break
            after_cursor = page_info.get("endCursor", "")
        except Exception as e:
            print(f"API exception: {e}")
            break

    return reviews

async def main():
    result = await asyncio.to_thread(_scrape_rt)
    print(f"\nTotal RT reviews: {len(result)}")

if __name__ == "__main__":
    asyncio.run(main())
