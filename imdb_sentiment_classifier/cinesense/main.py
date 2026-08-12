import asyncio
import sys
import textwrap

from cinesense.ml.classifier import classify_reviews, verdict_for
from cinesense.ml.train import build_pipeline
from cinesense.utils.aggregator import aggregate_reviews, flatten_sources
from cinesense.utils.title_resolver import search_titles

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def _print_results(title: str, classified: list[dict], source_breakdown: dict[str, int]) -> None:
    pos = sum(1 for row in classified if row["sentiment"] == "Positive")
    neg = len(classified) - pos
    avg_pos = sum(row["prob_pos"] for row in classified) / len(classified)
    print(f"\nSentiment analysis: {title}")
    print("-" * 72)
    for source, count in source_breakdown.items():
        print(f"{source:18} {count}")
    print("-" * 72)
    for index, row in enumerate(classified[:25], start=1):
        snippet = textwrap.shorten(row["text"], width=120, placeholder="...")
        print(f"{index:>2}. {row['sentiment']:<8} {row['confidence']:.0%} [{row['source']}] {snippet}")
    if len(classified) > 25:
        print(f"... and {len(classified) - 25} more reviews")
    print("-" * 72)
    print(f"Total reviews analysed : {len(classified)}")
    print(f"Positive               : {pos}")
    print(f"Negative               : {neg}")
    print(f"Avg positive probability: {avg_pos:.1%}")
    print(f"Verdict                : {verdict_for(avg_pos)}\n")


def main() -> None:
    print("CineSense")
    pipeline = build_pipeline()

    while True:
        try:
            query = input("Enter a movie or series title (or 'quit'): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break
        if not query:
            continue
        if query.lower() in {"q", "quit", "exit"}:
            print("Goodbye.")
            break

        requested_type = input("Type [movie/series/auto]: ").strip().lower() or None
        if requested_type == "auto":
            requested_type = None

        results = search_titles(query, requested_type)
        if not results:
            print("No matching title found.")
            continue

        for index, item in enumerate(results, start=1):
            kind = "series" if item.media_type == "tv" else "movie"
            year = f" ({item.year})" if item.year else ""
            print(f"{index}. {item.title}{year} - {kind}")

        try:
            choice = int(input(f"Select a title [1-{len(results)}]: ").strip()) - 1
            selected = results[choice]
        except Exception:
            print("Invalid selection.")
            continue

        print(f"Scraping reviews for {selected.title}...")
        source_reviews = asyncio.run(
            aggregate_reviews(
                selected.title,
                imdb_id=selected.imdb_id,
                tmdb_id=selected.tmdb_id,
                media_type=selected.media_type,
            )
        )
        review_items = flatten_sources(source_reviews)
        if not review_items:
            print("No written reviews found.")
            continue

        classified = classify_reviews(pipeline, [item.text for item in review_items])
        for row, item in zip(classified, review_items):
            row["source"] = item.source
        _print_results(
            selected.title,
            classified,
            {source: len(reviews) for source, reviews in source_reviews.items()},
        )


if __name__ == "__main__":
    main()
