from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Invoice(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int | None = None
    invoice_number: str
    vendor_name: str
    document_path: str
    subtotal: float = 0.0
    tax: float = 0.0
    total: float = 0.0
    currency: str = "INR"
    content: str
    content_hash: str
    created_by: int | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)

    @staticmethod
    def _normalize_text(text: str) -> str:
        cleaned = text.replace("\x00", " ").replace("\r", "\n")
        cleaned = re.sub(r"[â– â–¡â–ªâ–¸â—â—†]", "â‚¹", cleaned)
        lines = [re.sub(r"[ \t]+", " ", line).strip() for line in cleaned.splitlines()]
        return "\n".join(line for line in lines if line)

    @staticmethod
    def _coerce_amount(value: str | None) -> float:
        if not value:
            return 0.0
        cleaned = re.sub(r"[^\d.,\-]", "", str(value)).strip()
        if not cleaned:
            return 0.0
        if cleaned.count(",") > 0 and cleaned.count(".") == 0:
            cleaned = cleaned.replace(",", ".")
        elif cleaned.count(",") > 0 and cleaned.count(".") > 0:
            cleaned = cleaned.replace(",", "")
        try:
            return round(float(cleaned), 2)
        except ValueError:
            return 0.0

    @classmethod
    def _find_amount(cls, text: str, labels: list[str]) -> float:
        amt_pat = r"[â‚¹$â‚¬Â£]?\s*-?[\d,]+(?:\.\d{1,2})?"
        for label in labels:
            escaped = re.escape(label).replace(r"\ ", r"\s+")
            m = re.search(rf"(?im)\b{escaped}\b[^\n]{{0,30}}?({amt_pat})", text)
            if m:
                return cls._coerce_amount(m.group(1))
        return 0.0

    @staticmethod
    def _extract_currency(text: str) -> str:
        if "â‚¹" in text or re.search(r"\bINR\b", text, re.IGNORECASE):
            return "INR"
        if "â‚¬" in text or re.search(r"\bEUR\b", text, re.IGNORECASE):
            return "EUR"
        if "Â£" in text or re.search(r"\bGBP\b", text, re.IGNORECASE):
            return "GBP"
        if "$" in text or re.search(r"\bUSD\b", text, re.IGNORECASE):
            return "USD"
        return "INR"

    @classmethod
    def from_extracted(
        cls,
        extracted_fields: dict[str, Any],
        raw_text: str,
        document_path: str | Path,
        created_by: int | None = None,
    ) -> "Invoice":
        normalized = cls._normalize_text(raw_text)
        digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()

        inv_number = (
            extracted_fields.get("document_number")
            or f"INV-{digest[:10].upper()}"
        )
        vendor = (
            extracted_fields.get("vendor_name")
            or str(Path(document_path).stem)
        )
        subtotal = float(extracted_fields.get("subtotal") or 0.0)
        tax      = float(extracted_fields.get("tax") or 0.0)
        total    = float(extracted_fields.get("total") or 0.0)

        if total == 0.0 and subtotal > 0.0:
            total = round(subtotal + tax, 2)
        if subtotal == 0.0 and total > 0.0:
            subtotal = round(max(total - tax, 0.0), 2)

        currency = extracted_fields.get("currency") or cls._extract_currency(normalized)

        metadata: dict[str, Any] = {
            "source_name": Path(document_path).name,
            "kind": extracted_fields.get("kind", "unknown"),
        }
        skip = {"vendor_name", "subtotal", "tax", "total", "currency", "kind"}
        for k, v in extracted_fields.items():
            if k not in skip and v not in (None, "", 0.0, [], {}):
                metadata[k] = v

        return cls(
            invoice_number=str(inv_number)[:64],
            vendor_name=str(vendor)[:255],
            document_path=str(document_path),
            subtotal=subtotal,
            tax=tax,
            total=total,
            currency=currency,
            content=normalized,
            content_hash=digest,
            created_by=created_by,
            metadata=metadata,
        )

    @classmethod
    def from_text(
        cls,
        text: str,
        document_path: str | Path,
        created_by: int | None = None,
    ) -> "Invoice":
        normalized = cls._normalize_text(text)
        fallback_seed = normalized if normalized else str(document_path)
        digest = hashlib.sha256(fallback_seed.encode("utf-8")).hexdigest()

        invoice_match = re.search(
            r"(?im)\binvoice(?:\s*(?:number|no|#))?\b[^\w-]*([A-Z0-9][A-Z0-9._/-]{1,})",
            normalized,
        )
        vendor_match = re.search(
            r"(?im)\b(?:vendor|seller|from)\b[^\n:]*[:\-]?\s*(.+)$", normalized
        )

        subtotal = cls._find_amount(normalized, ["subtotal", "sub total", "net amount", "amount before tax"])
        tax      = cls._find_amount(normalized, ["tax", "vat", "gst", "cgst", "sgst", "igst"])
        total    = cls._find_amount(normalized, ["net pay", "grand total", "amount due", "total payable", "invoice total", "total"])

        if total == 0.0 and subtotal > 0.0:
            total = round(subtotal + tax, 2)
        if subtotal == 0.0 and total > 0.0:
            subtotal = round(max(total - tax, 0.0), 2)

        vendor_name = vendor_match.group(1).strip() if vendor_match else ""
        if not vendor_name:
            lines = [l.strip() for l in normalized.splitlines() if l.strip()]
            vendor_name = lines[0] if lines else Path(document_path).stem

        invoice_number = invoice_match.group(1).strip() if invoice_match else f"INV-{digest[:10].upper()}"

        return cls(
            invoice_number=invoice_number,
            vendor_name=vendor_name[:255],
            document_path=str(document_path),
            subtotal=float(subtotal or 0.0),
            tax=float(tax or 0.0),
            total=float(total or 0.0),
            currency=cls._extract_currency(normalized),
            content=normalized,
            content_hash=digest,
            created_by=created_by,
            metadata={"source_name": Path(document_path).name},
        )
