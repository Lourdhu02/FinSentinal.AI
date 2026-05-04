from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


DocumentKind = Literal[
    "invoice",
    "salary_slip",
    "bank_statement",
    "credit_debit_note",
    "gst_return",
    "purchase_order",
    "unknown",
]


class ExtractedDocument(BaseModel):

    kind: DocumentKind = "unknown"
    document_path: str = ""
    raw_text: str = ""

    document_number: str = ""
    document_date: str = ""
    period: str = ""

    vendor_or_company: str = ""
    gstin: str = ""
    pan: str = ""
    customer_or_employee: str = ""
    employee_id: str = ""
    designation: str = ""
    department: str = ""
    bank_name: str = ""
    account_number: str = ""

    currency: str = "INR"
    gross_amount: float = 0.0
    tax_amount: float = 0.0
    total_deductions: float = 0.0
    net_amount: float = 0.0

    basic_salary: float = 0.0
    hra: float = 0.0
    conveyance: float = 0.0
    medical_allowance: float = 0.0
    special_allowance: float = 0.0
    performance_bonus: float = 0.0
    pf_employee: float = 0.0
    esi: float = 0.0
    tds: float = 0.0
    professional_tax: float = 0.0

    opening_balance: float = 0.0
    closing_balance: float = 0.0
    total_credits: float = 0.0
    total_debits: float = 0.0

    taxable_value: float = 0.0
    cgst: float = 0.0
    sgst: float = 0.0
    igst: float = 0.0
    total_tax: float = 0.0

    note_type: str = ""
    reason: str = ""
    original_invoice: str = ""

    po_number: str = ""
    delivery_date: str = ""
    payment_terms: str = ""
    line_items: list[dict[str, Any]] = Field(default_factory=list)

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    extraction_issues: list[str] = Field(default_factory=list)
