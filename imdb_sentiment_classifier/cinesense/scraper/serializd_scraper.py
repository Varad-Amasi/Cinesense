import asyncio
import re

from cinesense.config import DEFAULT_MAX_REVIEWS_PER_SOURCE
from cinesense.scraper.common import clean_text, headers, slugify, unique_keep_order


async def _scrape_async(title: str, max_reviews: int) -> list[str]:
    try:
        from playwright.async_api import async_playwright
    except Exception:
        return []

    url = f"https://www.serializd.com/show/{slugify(title, '-')}/reviews"
    reviews: list[str] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(user_agent=headers()["User-Agent"])
        try:
            await page.goto(url, wait_until="networkidle", timeout=45000)
            stagnant_rounds = 0
            previous_count = 0
            while len(reviews) < max_reviews and stagnant_rounds < 4:
                await page.mouse.wheel(0, 3500)
                await page.wait_for_timeout(1200)
                for label in ("Load more", "Show more", "More"):
                    button = page.get_by_text(label, exact=False)
                    if await button.count():
                        try:
                            await button.first.click(timeout=1200)
                            await page.wait_for_timeout(1200)
                        except Exception:
                            pass
                texts = await page.locator("article, [class*='review'], [data-testid*='review']").all_inner_texts()
                for text in texts:
                    cleaned = clean_text(text)
                    if 40 < len(cleaned) < 6000 and not re.search(r"^\d+(\.\d+)?\s*/\s*5", cleaned):
                        reviews.append(cleaned)
                reviews = unique_keep_order(reviews)
                stagnant_rounds = stagnant_rounds + 1 if len(reviews) == previous_count else 0
                previous_count = len(reviews)
        except Exception:
            pass
        finally:
            await browser.close()

    return unique_keep_order(reviews)[:max_reviews]


def scrape(
    title: str,
    imdb_id: str,
    tmdb_id: str,
    media_type: str,
    max_reviews: int = DEFAULT_MAX_REVIEWS_PER_SOURCE,
) -> list[str]:
    del imdb_id, tmdb_id
    if media_type != "tv":
        return []
    try:
        return asyncio.run(_scrape_async(title, max_reviews))
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(_scrape_async(title, max_reviews))
        finally:
            loop.close()
