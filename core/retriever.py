from __future__ import annotations

import re

from core.embedder import LocalEmbedder
from database.vector_store import FAISSVectorStore


class Retriever:
    def __init__(self, embedder: LocalEmbedder, vector_store: FAISSVectorStore) -> None:
        self.embedder = embedder
        self.vector_store = vector_store

    def retrieve(self, query: str, top_k: int = 5) -> list[dict]:
        query_embedding = self.embedder.embed_query(query)
        return self.vector_store.search(query_embedding, top_k=top_k)

    def analyze_query(self, query: str) -> dict:
        normalized = re.sub(r"\s+", " ", query.strip().lower())
        if any(token in normalized for token in ("total", "sum", "spend")):
            return {"kind": "total", "target": None, "query": normalized}
        if "how many" in normalized or "count" in normalized:
            return {
                "kind": "count",
                "target": self._extract_count_target(normalized),
                "query": normalized,
            }
        return {"kind": "llm", "target": None, "query": normalized}

    def _extract_count_target(self, query: str) -> str | None:
        how_many_match = re.search(
            r"\bhow many\s+([a-z][a-z0-9 _-]*?)(?:\s+(?:were|was|are|is|have|has|did|do|purchased|bought|ordered|found|in)\b|$)",
            query,
        )
        count_match = re.search(
            r"\bcount\s+([a-z][a-z0-9 _-]*?)(?:\s+(?:were|was|are|is|have|has|purchased|bought|ordered|found|in)\b|$)",
            query,
        )
        candidate = how_many_match.group(1) if how_many_match else count_match.group(1) if count_match else None
        if not candidate:
            return None
        cleaned = re.sub(r"\b(total|all|items|item|purchases|purchase)\b", "", candidate).strip(" ?.")
        cleaned = re.sub(r"\s+", " ", cleaned)
        if not cleaned:
            return None
        if cleaned.endswith("s") and len(cleaned) > 3:
            cleaned = cleaned[:-1]
        return cleaned
