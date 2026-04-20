from __future__ import annotations

import hashlib

from pydantic import BaseModel, Field

from models.invoice import Invoice


class VerificationResult(BaseModel):
    content_hash: str
    duplicate: bool
    duplicate_invoice_id: int | None = None
    totals_valid: bool
    computed_total: float
    tax_rate: float = 0.0
    issues: list[str] = Field(default_factory=list)


class InvoiceVerifier:
    def calculate_hash(self, content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def verify_invoice(self, invoice: Invoice, db_manager: object | None = None) -> VerificationResult:
        content_hash = invoice.content_hash or self.calculate_hash(invoice.content)
        expected_total = round(invoice.subtotal + invoice.tax, 2)
        totals_valid = abs(expected_total - invoice.total) <= 0.05
        issues: list[str] = []
        if not totals_valid:
            issues.append(
                f"Total mismatch: expected {expected_total:.2f}, found {invoice.total:.2f}"
            )
        duplicate_invoice_id = None
        duplicate = False
        if db_manager is not None and hasattr(db_manager, "get_invoice_by_hash"):
            existing = db_manager.get_invoice_by_hash(content_hash)
            if existing is not None and existing.id != invoice.id:
                duplicate = True
                duplicate_invoice_id = existing.id
                issues.append(f"Duplicate content detected with invoice id {existing.id}")
        tax_rate = round(invoice.tax / invoice.subtotal, 4) if invoice.subtotal else 0.0
        return VerificationResult(
            content_hash=content_hash,
            duplicate=duplicate,
            duplicate_invoice_id=duplicate_invoice_id,
            totals_valid=totals_valid,
            computed_total=expected_total,
            tax_rate=tax_rate,
            issues=issues,
        )
