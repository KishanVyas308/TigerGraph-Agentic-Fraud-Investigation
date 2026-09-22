"""Embedding generation service for GraphRAG using SentenceTransformers with resilient fallback."""

import hashlib
import math
from typing import List, Optional

from backend.app.utils.logging import get_logger

logger = get_logger("rag.embeddings")

_MODEL_INSTANCE = None
_MODEL_ATTEMPTED = False
EMBEDDING_DIM = 384


def _get_sentence_transformer():
    """Lazily load SentenceTransformer model if available."""
    global _MODEL_INSTANCE, _MODEL_ATTEMPTED
    if not _MODEL_ATTEMPTED:
        _MODEL_ATTEMPTED = True
        try:
            from sentence_transformers import SentenceTransformer
            _MODEL_INSTANCE = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("Loaded SentenceTransformer ('all-MiniLM-L6-v2') successfully.")
        except Exception as exc:
            logger.warning("SentenceTransformer model unavailable (%s). Using deterministic vector engine.", exc)
            _MODEL_INSTANCE = None
    return _MODEL_INSTANCE


def _deterministic_vector(text: str, dim: int = EMBEDDING_DIM) -> List[float]:
    """Generate a deterministic normalized pseudo-embedding from text."""
    vec = [0.0] * dim
    words = text.lower().split()
    if not words:
        return vec

    for word in words:
        h = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16)
        idx = h % dim
        val = ((h >> 8) % 1000) / 1000.0 - 0.5
        vec[idx] += val

    # L2 normalize
    norm = math.sqrt(sum(x * x for x in vec))
    if norm > 0:
        vec = [x / norm for x in vec]
    return vec


def compute_embedding(text: str) -> List[float]:
    """Compute 384-dimensional vector embedding for given text."""
    model = _get_sentence_transformer()
    if model is not None:
        try:
            arr = model.encode(text, normalize_embeddings=True)
            return [float(x) for x in arr]
        except Exception as exc:
            logger.warning("Model inference error (%s); falling back to deterministic vector.", exc)

    return _deterministic_vector(text, dim=EMBEDDING_DIM)


def compute_embeddings(texts: List[str]) -> List[List[float]]:
    """Compute embeddings for a batch of texts."""
    model = _get_sentence_transformer()
    if model is not None:
        try:
            arrs = model.encode(texts, normalize_embeddings=True)
            return [[float(x) for x in arr] for arr in arrs]
        except Exception as exc:
            logger.warning("Batch inference error (%s); falling back to deterministic vectors.", exc)

    return [_deterministic_vector(t, dim=EMBEDDING_DIM) for t in texts]


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if len(vec1) != len(vec2) or len(vec1) == 0:
        return 0.0

    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))

    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0
    return max(-1.0, min(1.0, dot / (norm1 * norm2)))
