import json
import chromadb
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer

COLLECTION_NAME = "fleet_social_corpus"
DATA_DIR = Path(__file__).parent.parent / "data"

_embedder = None
_client = None
_collection = None
_corpus_size = 0


def _get_embedder():
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedder


def _get_collection():
    global _client, _collection
    if _collection is not None:
        return _collection
    persist_dir = str(DATA_DIR / "chroma_db")
    _client = chromadb.PersistentClient(path=persist_dir)
    try:
        _collection = _client.get_collection(COLLECTION_NAME)
    except Exception:
        _collection = _client.create_collection(
            COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
        )
    return _collection


def seed_corpus():
    collection = _get_collection()
    if collection.count() > 0:
        return collection.count()

    corpus_file = DATA_DIR / "seed_corpus.json"
    if not corpus_file.exists():
        return 0

    with open(corpus_file) as f:
        posts = json.load(f)

    embedder = _get_embedder()
    embeddings = embedder.encode(posts, show_progress_bar=False).tolist()
    ids = [f"seed_{i}" for i in range(len(posts))]

    collection.add(ids=ids, embeddings=embeddings, documents=posts)
    return len(posts)


def get_corpus_size() -> int:
    global _corpus_size
    if _corpus_size == 0:
        collection = _get_collection()
        _corpus_size = collection.count()
    return _corpus_size


def compute_competition_score(tag: str) -> float:
    embedder = _get_embedder()
    collection = _get_collection()
    tag_embedding = embedder.encode([tag], show_progress_bar=False).tolist()

    results = collection.query(
        query_embeddings=tag_embedding, n_results=min(10, collection.count())
    )

    distances = results.get("distances", [[]])[0]
    if not distances:
        return 0.0

    avg_similarity = 1.0 - np.mean(distances)
    score = max(0.0, min(100.0, avg_similarity * 100.0))
    return round(score, 1)


def get_topic_embedding(text: str) -> np.ndarray:
    embedder = _get_embedder()
    return embedder.encode([text], show_progress_bar=False)[0]
