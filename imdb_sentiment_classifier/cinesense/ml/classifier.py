from functools import lru_cache

from cinesense.ml.train import build_pipeline

THRESHOLDS = [
    (0.75, "WATCH"),
    (0.55, "WORTH WATCHING"),
    (0.45, "MIXED"),
    (0.30, "SKIP"),
    (0.00, "HARD SKIP"),
]


@lru_cache(maxsize=1)
def get_pipeline():
    return build_pipeline()


def classify_reviews(pipeline, reviews: list[str]) -> list[dict]:
    probas = pipeline.predict_proba(reviews)
    results: list[dict] = []
    for text, proba in zip(reviews, probas):
        prob_neg, prob_pos = float(proba[0]), float(proba[1])
        sentiment = "Positive" if prob_pos >= 0.5 else "Negative"
        results.append({
            "text": text,
            "sentiment": sentiment,
            "label": sentiment,
            "prob_pos": prob_pos,
            "prob_neg": prob_neg,
            "confidence": max(prob_pos, prob_neg),
        })
    return results


def verdict_for(avg_positive_prob: float) -> str:
    for threshold, verdict in THRESHOLDS:
        if avg_positive_prob >= threshold:
            return verdict
    return "HARD SKIP"
