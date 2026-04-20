from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from core.anomaly import AnomalyDetector
from core.embedder import LocalEmbedder
from core.ingestion import IngestionService
from core.llm_engine import OllamaEngine
from core.retriever import Retriever
from core.verifier import InvoiceVerifier
from database.db_manager import DatabaseManager
from database.vector_store import FAISSVectorStore
from models.invoice import Invoice
from security.audit_logger import AuditLogger


class FinSentinelPipeline:
    def __init__(
        self,
        db_manager: DatabaseManager | None = None,
        ingestion_service: IngestionService | None = None,
        embedder: LocalEmbedder | None = None,
        vector_store: FAISSVectorStore | None = None,
        verifier: InvoiceVerifier | None = None,
        anomaly_detector: AnomalyDetector | None = None,
        llm_engine: OllamaEngine | None = None,
        audit_logger: AuditLogger | None = None,
    ) -> None:
        self.db = db_manager or DatabaseManager()
        self.ingestion = ingestion_service or IngestionService()
        self.embedder = embedder or LocalEmbedder()
        self.vector_store = vector_store or FAISSVectorStore(dimension=self.embedder.dimension)
        self.retriever = Retriever(self.embedder, self.vector_store)
        self.verifier = verifier or InvoiceVerifier()
        self.anomaly_detector = anomaly_detector or AnomalyDetector()
        self.llm_engine = llm_engine or OllamaEngine()
        self.audit_logger = audit_logger or AuditLogger(self.db)

    def ingest_and_store(self, source_path: str | Path, user_id: int | None = None) -> dict[str, Any]:
        path = Path(source_path)
        source_files = self.ingestion.get_supported_files(path)
        documents = self.ingestion.ingest(path)
        processed: list[dict[str, Any]] = []
        stored_count = 0
        duplicate_count = 0
        error_count = 0
        for document in documents:
            try:
                source_text = document.text if document.text else ""
                if document.error and not source_text:
                    raise ValueError(document.error)
                invoice = self._build_invoice(document.path, source_text, user_id)
                verification = self.verifier.verify_invoice(invoice, self.db)
                anomaly = self.anomaly_detector.score(invoice.total, self.db.get_invoice_totals())
                invoice.metadata.update(
                    {
                        "file_type": document.file_type,
                        "verification": verification.model_dump(),
                        "anomaly": anomaly.model_dump(),
                    }
                )
                if verification.duplicate:
                    duplicate_count += 1
                    processed.append(
                        {
                            "path": document.path,
                            "status": "duplicate",
                            "invoice_number": invoice.invoice_number,
                            "duplicate_invoice_id": verification.duplicate_invoice_id,
                        }
                    )
                    continue
                stored_invoice = self.db.create_invoice(invoice)
                chunks = self._chunk_text(invoice.content)
                embeddings = self.embedder.embed_texts(chunks)
                metadata = [
                    {
                        "invoice_id": stored_invoice.id,
                        "invoice_number": stored_invoice.invoice_number,
                        "vendor_name": stored_invoice.vendor_name,
                        "document_path": stored_invoice.document_path,
                        "text": chunk,
                        "chunk_index": index,
                        "content_hash": stored_invoice.content_hash,
                    }
                    for index, chunk in enumerate(chunks)
                ]
                self.vector_store.add(embeddings, metadata)
                stored_count += 1
                processed.append(
                    {
                        "path": document.path,
                        "status": "stored",
                        "invoice_id": stored_invoice.id,
                        "invoice_number": stored_invoice.invoice_number,
                        "vendor_name": stored_invoice.vendor_name,
                        "verification": verification.model_dump(),
                        "anomaly": anomaly.model_dump(),
                    }
                )
            except Exception as exc:
                error_count += 1
                processed.append(
                    {
                        "path": document.path,
                        "status": "error",
                        "error": str(exc),
                    }
                )
        self.vector_store.save()
        return {
            "processed_count": len(source_files),
            "stored_count": stored_count,
            "duplicate_count": duplicate_count,
            "error_count": error_count,
            "success_count": stored_count,
            "failed_count": max(0, len(source_files) - stored_count),
            "documents": processed,
        }

    def query(self, question: str, user_id: int | None = None, top_k: int = 5) -> dict[str, Any]:
        route = self.retriever.analyze_query(question)
        results = self.retriever.retrieve(question, top_k=top_k)
        invoice_summaries = self._build_invoice_summaries(results)
        deterministic_response = self._handle_structured_query(route)
        response = deterministic_response if deterministic_response is not None else self.llm_engine.generate(
            question,
            results,
            invoice_summaries,
        )
        self.audit_logger.log_interaction(user_id, "query", question, response)
        return {
            "query": question,
            "response": response,
            "results": results,
            "invoice_summaries": invoice_summaries,
        }

    def _build_invoice_summaries(self, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        summaries: list[dict[str, Any]] = []
        seen_ids: set[int] = set()
        for result in results:
            invoice_id = result.get("invoice_id")
            if not isinstance(invoice_id, int) or invoice_id in seen_ids:
                continue
            invoice = self.db.get_invoice_by_id(invoice_id)
            if invoice is None:
                continue
            verification = self.verifier.verify_invoice(invoice, self.db)
            anomaly = self.anomaly_detector.score(
                invoice.total,
                self.db.get_invoice_totals(exclude_invoice_id=invoice.id),
            )
            summaries.append(
                {
                    "invoice_id": invoice.id,
                    "invoice_number": invoice.invoice_number,
                    "vendor_name": invoice.vendor_name,
                    "total": invoice.total,
                    "verification": verification.model_dump(),
                    "anomaly": anomaly.model_dump(),
                }
            )
            seen_ids.add(invoice_id)
        return summaries

    def _build_invoice(self, document_path: str | Path, text: str, user_id: int | None) -> Invoice:
        safe_text = text if text and text.strip() else Path(document_path).stem
        try:
            return Invoice.from_text(safe_text, document_path, created_by=user_id)
        except Exception:
            return Invoice.from_text(Path(document_path).stem, document_path, created_by=user_id)

    def _handle_structured_query(self, route: dict[str, Any]) -> str | None:
        kind = str(route.get("kind", "llm"))
        if kind == "total":
            invoices = self.db.get_all_invoices()
            total_spend = sum(float(invoice.total) for invoice in invoices)
            currency_symbol = self._currency_symbol(invoices)
            return f"Total spend is {currency_symbol}{self._format_number(total_spend)}"
        if kind == "count":
            target = route.get("target")
            if not target:
                return None
            count = self._count_items(str(target))
            label = self._pluralize_target(str(target), count)
            return f"Total {label} purchased: {count}"
        return None

    def _count_items(self, target: str) -> int:
        normalized_target = self._normalize_target(target)
        line_items = self.db.get_all_line_items()
        total_quantity = 0
        matched = False
        for item in line_items:
            description = self._normalize_target(str(item.get("description", "")))
            if normalized_target and normalized_target in description:
                total_quantity += int(item.get("quantity", 0))
                matched = True
        if matched:
            return total_quantity
        invoices = self.db.get_all_invoices()
        fallback_total = 0
        for invoice in invoices:
            for line in invoice.content.splitlines():
                lowered = line.lower()
                if normalized_target not in self._normalize_target(lowered):
                    continue
                quantity = self._extract_quantity_from_line(line)
                fallback_total += quantity
        return fallback_total

    def _extract_quantity_from_line(self, line: str) -> int:
        patterns = [
            r"(?i)\b(\d+)\s*(?:x|units?|pcs?|pieces?)?\s+[a-z]",
            r"(?i)[a-z]\s+(?:x|qty|quantity|units?|pcs?|pieces?)?\s*(\d+)\b",
        ]
        for pattern in patterns:
            match = re.search(pattern, line)
            if match:
                return max(0, int(match.group(1)))
        return 1

    def _normalize_target(self, value: str) -> str:
        cleaned = re.sub(r"[^a-z0-9 ]+", " ", value.lower())
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        if cleaned.endswith("s") and len(cleaned) > 3:
            cleaned = cleaned[:-1]
        return cleaned

    def _pluralize_target(self, target: str, count: int) -> str:
        normalized = target.strip().lower()
        if count == 1:
            return normalized[:-1] if normalized.endswith("s") and len(normalized) > 3 else normalized
        return normalized if normalized.endswith("s") else f"{normalized}s"

    def _currency_symbol(self, invoices: list[Invoice]) -> str:
        counts: dict[str, int] = {}
        for invoice in invoices:
            currency = invoice.currency or "USD"
            counts[currency] = counts.get(currency, 0) + 1
        if not counts:
            return "₹"
        if set(counts) == {"USD"}:
            return "₹"
        primary = max(counts, key=counts.get)
        return {
            "INR": "₹",
            "USD": "$",
            "EUR": "€",
            "GBP": "£",
        }.get(primary, "")

    def _format_number(self, value: float) -> str:
        rounded = round(value, 2)
        if abs(rounded - int(rounded)) < 1e-9:
            return f"{int(rounded):,}"
        return f"{rounded:,.2f}"

    def _chunk_text(self, text: str, chunk_size: int = 700, overlap: int = 120) -> list[str]:
        normalized = text.strip()
        if not normalized:
            return [""]
        chunks: list[str] = []
        start = 0
        while start < len(normalized):
            end = min(len(normalized), start + chunk_size)
            chunks.append(normalized[start:end])
            if end == len(normalized):
                break
            start = max(0, end - overlap)
        return chunks
