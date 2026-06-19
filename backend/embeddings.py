import json
import chromadb
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer
from backend.niche_manager import get_seed_corpus, get_active_niche

DATA_DIR = Path(__file__).parent.parent / "data"

_embedder = None
_client = None
_collections = {}
_corpus_sizes = {}


def _get_embedder():
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedder


def _get_collection(collection_name: str):
    global _client, _collections
    if collection_name in _collections:
        return _collections[collection_name]
    persist_dir = str(DATA_DIR / "chroma_db")
    if _client is None:
        _client = chromadb.PersistentClient(path=persist_dir)
    try:
        collection = _client.get_collection(collection_name)
    except Exception:
        collection = _client.create_collection(
            collection_name, metadata={"hnsw:space": "cosine"}
        )
    _collections[collection_name] = collection
    return collection


def seed_corpus(niche_id: str = None):
    if niche_id is None:
        niche_id = get_active_niche()

    collection = _get_collection(niche_id)
    if collection.count() > 0:
        return collection.count()

    posts = get_seed_corpus(niche_id)
    if not posts:
        return 0

    embedder = _get_embedder()
    embeddings = embedder.encode(posts, show_progress_bar=False).tolist()
    ids = [f"seed_{i}" for i in range(len(posts))]

    collection.add(ids=ids, embeddings=embeddings, documents=posts)
    return len(posts)


def get_corpus_size(niche_id: str = None) -> int:
    if niche_id is None:
        niche_id = get_active_niche()

    if niche_id not in _corpus_sizes or _corpus_sizes[niche_id] == 0:
        collection = _get_collection(niche_id)
        _corpus_sizes[niche_id] = collection.count()
    return _corpus_sizes[niche_id]


def compute_competition_score(tag: str, niche_id: str = None) -> float:
    if niche_id is None:
        niche_id = get_active_niche()

    embedder = _get_embedder()
    collection = _get_collection(niche_id)
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
