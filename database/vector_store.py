from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import faiss
import numpy as np

from config import get_settings


class FAISSVectorStore:
    def __init__(self, index_path: str | Path | None = None, dimension: int = 384) -> None:
        self.settings = get_settings()
        self.index_path = Path(index_path or self.settings.faiss_index_path)
        self.metadata_path = self.index_path.with_suffix(f"{self.index_path.suffix}.meta.json")
        self.dimension = dimension
        self.index = faiss.IndexFlatL2(self.dimension)
        self.metadata: list[dict[str, Any]] = []
        if self.index_path.exists() and self.metadata_path.exists():
            self.load()

    def add(self, embeddings: np.ndarray, metadata: list[dict[str, Any]]) -> list[int]:
        matrix = np.asarray(embeddings, dtype=np.float32)
        if matrix.ndim == 1:
            matrix = matrix.reshape(1, -1)
        if matrix.size == 0:
            return []
        if matrix.shape[1] != self.dimension:
            raise ValueError(f"Embedding dimension mismatch: expected {self.dimension}, got {matrix.shape[1]}")
        if len(metadata) != matrix.shape[0]:
            raise ValueError("Metadata count must match embedding count.")
        start_index = len(self.metadata)
        self.index.add(matrix)
        self.metadata.extend(metadata)
        return list(range(start_index, start_index + len(metadata)))

    def search(self, query_embedding: np.ndarray, top_k: int = 5) -> list[dict[str, Any]]:
        if self.index.ntotal == 0:
            return []
        vector = np.asarray(query_embedding, dtype=np.float32)
        if vector.ndim == 1:
            vector = vector.reshape(1, -1)
        distances, indices = self.index.search(vector, min(top_k, self.index.ntotal))
        results: list[dict[str, Any]] = []
        for distance, index in zip(distances[0], indices[0]):
            if index < 0 or index >= len(self.metadata):
                continue
            item = dict(self.metadata[index])
            item["score"] = float(distance)
            item["vector_id"] = int(index)
            results.append(item)
        return results

    def save(self) -> None:
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(self.index_path))
        with self.metadata_path.open("w", encoding="utf-8") as metadata_file:
            json.dump({"dimension": self.dimension, "items": self.metadata}, metadata_file, ensure_ascii=False, indent=2)

    def load(self) -> None:
        self.index = faiss.read_index(str(self.index_path))
        with self.metadata_path.open("r", encoding="utf-8") as metadata_file:
            payload = json.load(metadata_file)
        self.dimension = int(payload.get("dimension", self.index.d))
        self.metadata = list(payload.get("items", []))

    def reset(self) -> None:
        self.index = faiss.IndexFlatL2(self.dimension)
        self.metadata = []
        self.save()
