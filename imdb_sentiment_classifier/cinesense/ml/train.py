import tarfile
import warnings
from pathlib import Path

import joblib
import requests
from sklearn.base import BaseEstimator, ClassifierMixin

from cinesense.config import DATA_DIR

ACL_IMDB_URL = "https://ai.stanford.edu/~amaas/data/sentiment/aclImdb_v1.tar.gz"
ACL_ARCHIVE = DATA_DIR / "aclImdb_v1.tar.gz"
ACL_EXTRACTED = DATA_DIR / "aclImdb"
PROCESSED_CACHE = DATA_DIR / "processed_training_corpus.joblib"
MODELS_DIR = Path("models")
MODEL_ARTIFACT = MODELS_DIR / "pipeline.joblib"


def _ensure_nltk_data() -> None:
    import nltk

    try:
        nltk.data.find("corpora/movie_reviews")
    except LookupError:
        nltk.download("movie_reviews", quiet=True)


def _load_nltk_movie_reviews() -> tuple[list[str], list[int]]:
    _ensure_nltk_data()
    from nltk.corpus import movie_reviews

    docs: list[str] = []
    labels: list[int] = []
    for category in movie_reviews.categories():
        for fileid in movie_reviews.fileids(category):
            docs.append(movie_reviews.raw(fileid))
            labels.append(1 if category == "pos" else 0)
    return docs, labels


def _download_stanford_dataset() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if ACL_ARCHIVE.exists():
        return
    with requests.get(ACL_IMDB_URL, stream=True, timeout=60) as resp:
        resp.raise_for_status()
        with ACL_ARCHIVE.open("wb") as f:
            for chunk in resp.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)


def _extract_stanford_dataset() -> None:
    if ACL_EXTRACTED.exists():
        return
    _download_stanford_dataset()
    with tarfile.open(ACL_ARCHIVE, "r:gz") as tar:
        tar.extractall(DATA_DIR)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace").strip()


def _load_stanford_reviews() -> tuple[list[str], list[int]]:
    _extract_stanford_dataset()
    docs: list[str] = []
    labels: list[int] = []
    for split in ("train", "test"):
        for label_name, label in (("pos", 1), ("neg", 0)):
            folder = ACL_EXTRACTED / split / label_name
            for path in sorted(folder.glob("*.txt")):
                docs.append(_read_text(path))
                labels.append(label)
    return docs, labels


def load_training_corpus(force_refresh: bool = False) -> tuple[list[str], list[int]]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if PROCESSED_CACHE.exists() and not force_refresh:
        cached = joblib.load(PROCESSED_CACHE)
        return cached["docs"], cached["labels"]

    stanford_docs, stanford_labels = _load_stanford_reviews()
    nltk_docs, nltk_labels = _load_nltk_movie_reviews()
    docs = stanford_docs + nltk_docs
    labels = stanford_labels + nltk_labels

    joblib.dump({"docs": docs, "labels": labels}, PROCESSED_CACHE, compress=3)
    return docs, labels


class TorchTextClassifier(BaseEstimator, ClassifierMixin):
    """sklearn-compatible linear classifier trained with PyTorch CUDA."""

    def __init__(
        self,
        epochs: int = 14,
        batch_size: int = 256,
        learning_rate: float = 0.01,
        weight_decay: float = 0.0001,
        random_state: int = 42,
        device: str = "cuda",
    ):
        self.epochs = epochs
        self.batch_size = batch_size
        self.learning_rate = learning_rate
        self.weight_decay = weight_decay
        self.random_state = random_state
        self.device = device

    def get_params(self, deep=True):
        return {
            "epochs": self.epochs,
            "batch_size": self.batch_size,
            "learning_rate": self.learning_rate,
            "weight_decay": self.weight_decay,
            "random_state": self.random_state,
            "device": self.device,
        }

    def set_params(self, **params):
        for key, value in params.items():
            setattr(self, key, value)
        return self

    def fit(self, X, y):
        import numpy as np
        import torch

        torch.manual_seed(self.random_state)
        self.classes_ = np.array([0, 1])
        self.n_features_in_ = X.shape[1]
        self.model_ = torch.nn.Linear(self.n_features_in_, 2).to(self.device)
        optimizer = torch.optim.AdamW(self.model_.parameters(), lr=self.learning_rate, weight_decay=self.weight_decay)
        loss_fn = torch.nn.CrossEntropyLoss()
        y_np = np.asarray(y, dtype="int64")
        rng = np.random.default_rng(self.random_state)

        self.model_.train()
        for _ in range(self.epochs):
            indices = rng.permutation(len(y_np))
            for start in range(0, len(indices), self.batch_size):
                batch_idx = indices[start:start + self.batch_size]
                xb = X[batch_idx]
                if hasattr(xb, "toarray"):
                    xb = xb.toarray()
                xb = torch.as_tensor(np.asarray(xb, dtype="float32"), device=self.device)
                yb = torch.as_tensor(y_np[batch_idx], dtype=torch.long, device=self.device)
                optimizer.zero_grad(set_to_none=True)
                loss = loss_fn(self.model_(xb), yb)
                loss.backward()
                optimizer.step()
        return self

    def predict_proba(self, X):
        import numpy as np
        import torch

        if X.shape[0] == 0:
            return np.empty((0, 2), dtype="float32")
        chunks = []
        self.model_.eval()
        with torch.inference_mode():
            for start in range(0, X.shape[0], self.batch_size):
                xb = X[start:start + self.batch_size]
                if hasattr(xb, "toarray"):
                    xb = xb.toarray()
                xb = torch.as_tensor(np.asarray(xb, dtype="float32"), device=self.device)
                chunks.append(torch.softmax(self.model_(xb), dim=1).cpu().numpy())
        return np.vstack(chunks)

    def predict(self, X):
        return self.predict_proba(X).argmax(axis=1)


class LoggedXGBTextClassifier(BaseEstimator, ClassifierMixin):
    """sklearn-compatible XGBoost text classifier with fit-time input logging."""

    def __init__(
        self,
        n_estimators: int = 600,
        learning_rate: float = 0.08,
        max_depth: int = 6,
        tree_method: str = "hist",
        device: str = "cuda",
        eval_metric: str = "logloss",
        random_state: int = 42,
        verbosity: int = 0,
    ):
        self.n_estimators = n_estimators
        self.learning_rate = learning_rate
        self.max_depth = max_depth
        self.tree_method = tree_method
        self.device = device
        self.eval_metric = eval_metric
        self.random_state = random_state
        self.verbosity = verbosity

    def get_params(self, deep=True):
        return {
            "n_estimators": self.n_estimators,
            "learning_rate": self.learning_rate,
            "max_depth": self.max_depth,
            "tree_method": self.tree_method,
            "device": self.device,
            "eval_metric": self.eval_metric,
            "random_state": self.random_state,
            "verbosity": self.verbosity,
        }

    def set_params(self, **params):
        for key, value in params.items():
            setattr(self, key, value)
        return self

    def fit(self, X, y):
        import numpy as np
        from xgboost import XGBClassifier

        print(f"GPU XGBoost input matrix: type={type(X).__name__}, shape={getattr(X, 'shape', None)}")
        self.model_ = XGBClassifier(
            n_estimators=self.n_estimators,
            learning_rate=self.learning_rate,
            max_depth=self.max_depth,
            tree_method=self.tree_method,
            device=self.device,
            eval_metric=self.eval_metric,
            random_state=self.random_state,
            verbosity=self.verbosity,
        )
        self.classes_ = np.array([0, 1])
        self.model_.fit(X, y)
        self.n_features_in_ = getattr(self.model_, "n_features_in_", X.shape[1])
        return self

    def predict_proba(self, X):
        return self.model_.predict_proba(X)

    def predict(self, X):
        return self.model_.predict(X)


def _build_backend():
    try:
        import numpy as np
        from xgboost import XGBClassifier

        clf = XGBClassifier(
            n_estimators=600,
            learning_rate=0.08,
            max_depth=6,
            tree_method="hist",
            device="cuda",
            eval_metric="logloss",
            random_state=42,
            verbosity=0,
        )
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")
            clf.fit(np.array([[0.0], [1.0]], dtype="float32"), np.array([0, 1]))
        if any("No visible GPU" in str(w.message) for w in captured):
            return None
        return LoggedXGBTextClassifier(), "GPU (XGBoost CUDA)"
    except Exception:
        pass

    try:
        import torch

        if torch.cuda.is_available():
            device_name = torch.cuda.get_device_name(0)
            return TorchTextClassifier(device="cuda"), f"GPU (PyTorch CUDA: {device_name})"
    except Exception:
        pass

    return None


def build_pipeline(force_refresh_data: bool = False, cross_validate: bool = False):
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.decomposition import TruncatedSVD
    from sklearn.metrics import accuracy_score
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import cross_val_score, train_test_split
    from sklearn.pipeline import Pipeline

    backend = _build_backend()
    if backend:
        classifier, backend_name = backend
    else:
        classifier = LogisticRegression(max_iter=3000, C=1.0, solver="lbfgs")
        backend_name = "CPU (scikit-learn)"

    print(f"Training backend selected: {backend_name}")
    print("Loading Stanford Large Movie Review Dataset + NLTK movie_reviews...")
    docs, labels = load_training_corpus(force_refresh=force_refresh_data)
    print(f"Loaded {len(docs)} training samples ({sum(labels)} positive / {len(labels) - sum(labels)} negative)")

    train_docs, test_docs, train_labels, test_labels = train_test_split(
        docs,
        labels,
        test_size=0.2,
        random_state=42,
        stratify=labels,
    )

    feature_steps = [
        ("tfidf", TfidfVectorizer(
            max_features=50_000,
            ngram_range=(1, 3),
            sublinear_tf=True,
            strip_accents="unicode",
            stop_words="english",
        )),
    ]
    if backend_name == "GPU (XGBoost CUDA)":
        feature_steps.append(("svd", TruncatedSVD(n_components=256, random_state=42)))

    pipeline = Pipeline(feature_steps + [("clf", classifier)])

    if cross_validate and backend_name == "CPU (scikit-learn)":
        scores = cross_val_score(pipeline, train_docs, train_labels, cv=5, scoring="accuracy")
        print(f"5-fold CV accuracy: {scores.mean():.2%} (+/- {scores.std():.2%})")

    pipeline.fit(train_docs, train_labels)
    training_accuracy = accuracy_score(train_labels, pipeline.predict(train_docs))
    test_accuracy = accuracy_score(test_labels, pipeline.predict(test_docs))
    print(f"Training accuracy: {training_accuracy:.2%}")
    print(f"Test Accuracy: {test_accuracy:.2%}")
    pipeline.training_accuracy_ = training_accuracy
    pipeline.test_accuracy_ = test_accuracy
    pipeline.training_backend_ = backend_name
    # Persist trained pipeline for faster subsequent startups
    try:
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        joblib.dump(pipeline, MODEL_ARTIFACT, compress=3)
        print(f"Saved trained pipeline to {MODEL_ARTIFACT}")
    except Exception as exc:
        print(f"Warning: failed to save pipeline: {exc}")
    return pipeline


def load_saved_pipeline() -> object | None:
    """Load a previously saved pipeline artifact if available."""
    try:
        if MODEL_ARTIFACT.exists():
            pl = joblib.load(MODEL_ARTIFACT)
            print(f"Loaded pipeline from {MODEL_ARTIFACT}")
            return pl
    except Exception as exc:
        print(f"Warning: failed to load saved pipeline: {exc}")
    return None
