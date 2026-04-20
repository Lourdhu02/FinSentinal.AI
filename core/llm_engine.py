from __future__ import annotations

import json
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from config import get_settings


class OllamaEngine:
    def __init__(self, model_name: str | None = None, endpoint: str = "http://127.0.0.1:11434/api/generate") -> None:
        self.settings = get_settings()
        self.model_name = model_name or self.settings.model_name
        self.endpoint = endpoint

    def build_prompt(
        self,
        query: str,
        retrieved_items: list[dict[str, Any]],
        invoice_summaries: list[dict[str, Any]],
    ) -> str:
        context_blocks: list[str] = []
        for index, item in enumerate(retrieved_items, start=1):
            snippet = str(item.get("text", "")).strip()
            snippet = snippet[:1200]
            context_blocks.append(
                f"Context {index}\nPath: {item.get('document_path', 'unknown')}\nVendor: {item.get('vendor_name', 'unknown')}\nInvoice: {item.get('invoice_number', 'unknown')}\nDistance: {item.get('score', 0.0):.4f}\nText: {snippet}"
            )
        summary_blocks: list[str] = []
        for summary in invoice_summaries:
            summary_blocks.append(
                json.dumps(summary, ensure_ascii=False)
            )
        joined_context = "\n\n".join(context_blocks) if context_blocks else "No retrieval context available."
        joined_summaries = "\n".join(summary_blocks) if summary_blocks else "No invoice summaries available."
        return (
            "You are a local financial analysis assistant.\n"
            "Use only the supplied context.\n"
            "Focus on descriptive explanations, anomaly interpretation, and evidence-backed reasoning.\n"
            "Do not invent arithmetic or counts that are not explicitly provided.\n\n"
            f"User Question:\n{query}\n\n"
            f"Retrieved Context:\n{joined_context}\n\n"
            f"Verification And Anomaly Data:\n{joined_summaries}\n"
        )

    def generate(
        self,
        query: str,
        retrieved_items: list[dict[str, Any]],
        invoice_summaries: list[dict[str, Any]],
    ) -> str:
        prompt = self.build_prompt(query, retrieved_items, invoice_summaries)
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1},
        }
        request = Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=120) as response:
                data = json.loads(response.read().decode("utf-8"))
            text = str(data.get("response", "")).strip()
            if text:
                return text
        except (URLError, TimeoutError, OSError, json.JSONDecodeError):
            pass
        return self._fallback_response(query, retrieved_items, invoice_summaries)

    def _fallback_response(
        self,
        query: str,
        retrieved_items: list[dict[str, Any]],
        invoice_summaries: list[dict[str, Any]],
    ) -> str:
        if not retrieved_items:
            return f"No indexed invoice context was found for: {query}"
        lines = [f"Query: {query}", "Retrieved evidence:"]
        for item in retrieved_items[:5]:
            lines.append(
                f"- {item.get('vendor_name', 'unknown')} / {item.get('invoice_number', 'unknown')} / {item.get('document_path', 'unknown')}"
            )
            snippet = str(item.get("text", "")).replace("\n", " ").strip()
            lines.append(snippet[:240])
        if invoice_summaries:
            lines.append("Verification and anomaly summary:")
            for summary in invoice_summaries[:5]:
                lines.append(json.dumps(summary, ensure_ascii=False))
        return "\n".join(lines)
