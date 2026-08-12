import random
import re
import time
from typing import Iterable

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]


def headers(extra: dict | None = None) -> dict:
    base = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "en-US,en;q=0.9",
    }
    if extra:
        base.update(extra)
    return base


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def unique_keep_order(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for item in items:
        text = clean_text(item)
        if text and text not in seen:
            seen.add(text)
            unique.append(text)
    return unique


def slugify(value: str, sep: str = "_") -> str:
    return re.sub(r"[^a-z0-9]+", sep, (value or "").lower()).strip(sep)


def polite_sleep(min_seconds: float = 0.35, max_seconds: float = 1.1) -> None:
    time.sleep(random.uniform(min_seconds, max_seconds))
