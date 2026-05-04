from __future__ import annotations

import hashlib
import os
import warnings

# Suppress noisy transformers/torch warnings
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
warnings.filterwarnings("ignore", message=".*__path__.*")
warnings.filterwarnings("ignore", category=FutureWarning)

import numpy as np

from config import get_settings


class LocalEmbedder:
    def __init__(self, model_name: str | None = None) -> None:
        self.settings = get_settings()
        self.model_name = model_name or self.settings.embedding_model
        self.dimension = 384
        self._model = None
        self._load_model()

    def _load_model(self) -> None:
        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name, device="cpu")
            if hasattr(self._model, "get_embedding_dimension"):
                detected_dimension = self._model.get_embedding_dimension()
            else:
                detected_dimension = self._model.get_sentence_embedding_dimension()
            if detected_dimension:
                self.dimension = int(detected_dimension)
        except Exception:
            self._model = None

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, self.dimension), dtype=np.float32)
        if self._model is not None:
            embeddings = self._model.encode(
                texts,
                batch_size=32,
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            return np.asarray(embeddings, dtype=np.float32)
        vectors = [self._fallback_embedding(text) for text in texts]
        return np.asarray(vectors, dtype=np.float32)

    def embed_query(self, text: str) -> np.ndarray:
        return self.embed_texts([text])[0]

    def _fallback_embedding(self, text: str) -> np.ndarray:
        seed = int.from_bytes(hashlib.sha256(text.encode("utf-8")).digest()[:8], "big") % (2**32)
        rng = np.random.default_rng(seed)
        vector = rng.standard_normal(self.dimension)
        norm = np.linalg.norm(vector)
        if norm == 0:
            return vector.astype(np.float32)
        return (vector / norm).astype(np.float32)

