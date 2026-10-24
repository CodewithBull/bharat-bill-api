"""Pydantic schemas for requests and responses."""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .gst import ALLOWED_GST_RATES, validate_gstin, validate_state_code


def _check_state_code(v: str) -> str:
    v = v.strip()
    if not validate_state_code(v):
        raise ValueError(f"Unknown GST state code: {v!r}. See GET /states.")
    return v


def _check_gstin(v: str | None) -> str | None:
    if v is None or v == "":
        return None
    v = v.strip().upper()
    if not validate_gstin(v):
        raise ValueError(f"Invalid GSTIN format: {v!r} (15 chars, e.g. 09ABCDE1234F1Z5)")
    return v


def _check_gst_rate(v: float) -> float:
    if v not in ALLOWED_GST_RATES:
        raise ValueError(f"GST rate must be one of {sorted(ALLOWED_GST_RATES)}")
    return v


# ---------------------------------------------------------------- customers
class CustomerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    gstin: str | None = None
    state_code: str
    phone: str | None = None
    email: str | None = None
    address: str | None = None

    _v_state = field_validator("state_code")(_check_state_code)
    _v_gstin = field_validator("gstin")(_check_gstin)


class CustomerOut(CustomerCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


# ----------------------------------------------------------------- products
class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    hsn: str | None = None
    rate: float = Field(ge=0)
    gst_rate: float = 18.0
    unit: str = "pcs"

    _v_rate = field_validator("gst_rate")(_check_gst_rate)


class ProductOut(ProductCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


# ----------------------------------------------------------------- invoices
class InvoiceItemCreate(BaseModel):
    description: str = Field(min_length=1, max_length=300)
    hsn: str | None = None
    quantity: float = Field(gt=0)
    rate: float = Field(ge=0)
    gst_rate: float = 18.0

    _v_rate = field_validator("gst_rate")(_check_gst_rate)


class InvoiceItemOut(InvoiceItemCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    taxable_value: float
    cgst_amount: float
    sgst_amount: float
    igst_amount: float
    total: float


class InvoiceCreate(BaseModel):
    seller_name: str = Field(min_length=1, max_length=200)
    seller_gstin: str | None = None
    seller_state_code: str
    seller_upi_id: str | None = None
    seller_address: str | None = None

    buyer_name: str = Field(min_length=1, max_length=200)
    buyer_gstin: str | None = None
    buyer_state_code: str
    customer_id: int | None = None

    issue_date: date | None = None
    items: list[InvoiceItemCreate] = Field(min_length=1)

    _v_seller_state = field_validator("seller_state_code")(_check_state_code)
    _v_buyer_state = field_validator("buyer_state_code")(_check_state_code)
    _v_seller_gstin = field_validator("seller_gstin")(_check_gstin)
    _v_buyer_gstin = field_validator("buyer_gstin")(_check_gstin)


class InvoiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    invoice_number: str
    issue_date: str
    seller_name: str
    seller_gstin: str | None
    seller_state_code: str
    seller_upi_id: str | None
    seller_address: str | None
    buyer_name: str
    buyer_gstin: str | None
    buyer_state_code: str
    customer_id: int | None
    subtotal: float
    cgst_amount: float
    sgst_amount: float
    igst_amount: float
    tax_amount: float
    round_off: float
    grand_total: float
    upi_link: str | None
    items: list[InvoiceItemOut] = []
