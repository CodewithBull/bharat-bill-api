"""SQLAlchemy models: customers, products, invoices and invoice items."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from .database import Base


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    gstin = Column(String(15), nullable=True)
    state_code = Column(String(2), nullable=False)
    phone = Column(String(20), nullable=True)
    email = Column(String(200), nullable=True)
    address = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    hsn = Column(String(20), nullable=True)
    rate = Column(Float, nullable=False, default=0.0)
    gst_rate = Column(Float, nullable=False, default=18.0)
    unit = Column(String(20), nullable=False, default="pcs")
    created_at = Column(DateTime, default=datetime.utcnow)


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    invoice_number = Column(String(30), unique=True, index=True, nullable=False)
    issue_date = Column(String(10), nullable=False)  # ISO date, YYYY-MM-DD

    seller_name = Column(String(200), nullable=False)
    seller_gstin = Column(String(15), nullable=True)
    seller_state_code = Column(String(2), nullable=False)
    seller_upi_id = Column(String(100), nullable=True)
    seller_address = Column(Text, nullable=True)

    buyer_name = Column(String(200), nullable=False)
    buyer_gstin = Column(String(15), nullable=True)
    buyer_state_code = Column(String(2), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)

    subtotal = Column(Float, nullable=False, default=0.0)
    cgst_amount = Column(Float, nullable=False, default=0.0)
    sgst_amount = Column(Float, nullable=False, default=0.0)
    igst_amount = Column(Float, nullable=False, default=0.0)
    tax_amount = Column(Float, nullable=False, default=0.0)
    round_off = Column(Float, nullable=False, default=0.0)
    grand_total = Column(Float, nullable=False, default=0.0)
    upi_link = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")


class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    description = Column(String(300), nullable=False)
    hsn = Column(String(20), nullable=True)
    quantity = Column(Float, nullable=False)
    rate = Column(Float, nullable=False)
    gst_rate = Column(Float, nullable=False)
    taxable_value = Column(Float, nullable=False)
    cgst_amount = Column(Float, nullable=False, default=0.0)
    sgst_amount = Column(Float, nullable=False, default=0.0)
    igst_amount = Column(Float, nullable=False, default=0.0)
    total = Column(Float, nullable=False)

    invoice = relationship("Invoice", back_populates="items")
