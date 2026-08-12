#!/usr/bin/env python3
"""Compatibility wrapper for the refactored CineSense package."""

from cinesense.main import main
from cinesense.ml.classifier import classify_reviews, verdict_for
from cinesense.ml.train import build_pipeline, load_training_corpus
from cinesense.scraper.imdb_scraper import scrape as scrape_reviews
from cinesense.utils.title_resolver import search_imdb_fallback as search_imdb


if __name__ == "__main__":
    main()
