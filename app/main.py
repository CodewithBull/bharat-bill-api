"""Bharat Bill API — FastAPI application.

Run:  uvicorn app.main:app --reload
Docs: http://127.0.0.1:8000/docs   (send X-API-Key: dev-key-change-me)
"""
from __future__ import annotations

import html as html_lib
from datetime import date

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from . import __version__
from .auth import require_api_key
from .database import Base, engine, get_db
from .gst import STATE_CODES, build_upi_link, compute_item_tax, money, validate_gstin
from .models import Customer, Invoice, InvoiceItem, Product
from .schemas import (
    CustomerCreate,
    CustomerOut,
    InvoiceCreate,
    InvoiceOut,
    ProductCreate,
    ProductOut,
)

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Bharat Bill API",
    version=__version__,
    description=(
        "GST billing API for small Indian shops and freelancers. "
        "Creates GST-correct invoices (CGST/SGST vs IGST automatically), "
        "with UPI payment links and a printable HTML invoice."
    ),
)

Auth = Depends(require_api_key)


# ------------------------------------------------------------------- health
@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok", "service": "bharat-bill-api", "version": __version__}


@app.get("/states", tags=["meta"], dependencies=[Auth])
def list_states():
    """GST state codes, e.g. 09 = Uttar Pradesh, 07 = Delhi, 27 = Maharashtra."""
    return STATE_CODES


@app.get("/validate/gstin/{gstin}", tags=["meta"], dependencies=[Auth])
def check_gstin(gstin: str):
    gstin = gstin.strip().upper()
    valid = validate_gstin(gstin)
    return {
        "gstin": gstin,
        "valid_format": valid,
        "state_code": gstin[:2] if valid else None,
        "state": STATE_CODES.get(gstin[:2]) if valid else None,
    }


# ---------------------------------------------------------------- customers
@app.post("/customers", response_model=CustomerOut, status_code=status.HTTP_201_CREATED,
          tags=["customers"], dependencies=[Auth])
def create_customer(payload: CustomerCreate, db: Session = Depends(get_db)):
    customer = Customer(**payload.model_dump())
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@app.get("/customers", response_model=list[CustomerOut], tags=["customers"], dependencies=[Auth])
def list_customers(db: Session = Depends(get_db)):
    return db.query(Customer).order_by(Customer.id).all()


@app.get("/customers/{customer_id}", response_model=CustomerOut,
         tags=["customers"], dependencies=[Auth])
def get_customer(customer_id: int, db: Session = Depends(get_db)):
    customer = db.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


# ----------------------------------------------------------------- products
@app.post("/products", response_model=ProductOut, status_code=status.HTTP_201_CREATED,
          tags=["products"], dependencies=[Auth])
def create_product(payload: ProductCreate, db: Session = Depends(get_db)):
    product = Product(**payload.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@app.get("/products", response_model=list[ProductOut], tags=["products"], dependencies=[Auth])
def list_products(db: Session = Depends(get_db)):
    return db.query(Product).order_by(Product.id).all()


@app.get("/products/{product_id}", response_model=ProductOut,
         tags=["products"], dependencies=[Auth])
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


# ----------------------------------------------------------------- invoices
def _next_invoice_number(db: Session, issue: date) -> str:
    count = db.query(Invoice).count()
    return f"INV-{issue.year}-{count + 1:04d}"


@app.post("/invoices", response_model=InvoiceOut, status_code=status.HTTP_201_CREATED,
          tags=["invoices"], dependencies=[Auth])
def create_invoice(payload: InvoiceCreate, db: Session = Depends(get_db)):
    if payload.customer_id is not None and not db.get(Customer, payload.customer_id):
        raise HTTPException(status_code=404, detail="customer_id not found")

    issue = payload.issue_date or date.today()
    intra_state = payload.seller_state_code == payload.buyer_state_code

    subtotal = cgst = sgst = igst = 0.0
    item_rows: list[InvoiceItem] = []
    for item in payload.items:
        taxable = money(item.quantity * item.rate)
        tax = compute_item_tax(taxable, item.gst_rate, intra_state)
        subtotal = money(subtotal + taxable)
        cgst = money(cgst + tax["cgst_amount"])
        sgst = money(sgst + tax["sgst_amount"])
        igst = money(igst + tax["igst_amount"])
        item_rows.append(
            InvoiceItem(
                description=item.description,
                hsn=item.hsn,
                quantity=item.quantity,
                rate=item.rate,
                gst_rate=item.gst_rate,
                taxable_value=taxable,
                cgst_amount=tax["cgst_amount"],
                sgst_amount=tax["sgst_amount"],
                igst_amount=tax["igst_amount"],
                total=money(taxable + tax["tax_amount"]),
            )
        )

    tax_total = money(cgst + sgst + igst)
    before_round = money(subtotal + tax_total)
    grand_total = float(round(before_round))
    round_off = money(grand_total - before_round)

    invoice_number = _next_invoice_number(db, issue)
    upi_link = None
    if payload.seller_upi_id:
        upi_link = build_upi_link(
            payload.seller_upi_id, payload.seller_name, grand_total,
            note=f"Invoice {invoice_number}",
        )

    invoice = Invoice(
        invoice_number=invoice_number,
        issue_date=issue.isoformat(),
        seller_name=payload.seller_name,
        seller_gstin=payload.seller_gstin,
        seller_state_code=payload.seller_state_code,
        seller_upi_id=payload.seller_upi_id,
        seller_address=payload.seller_address,
        buyer_name=payload.buyer_name,
        buyer_gstin=payload.buyer_gstin,
        buyer_state_code=payload.buyer_state_code,
        customer_id=payload.customer_id,
        subtotal=subtotal,
        cgst_amount=cgst,
        sgst_amount=sgst,
        igst_amount=igst,
        tax_amount=tax_total,
        round_off=round_off,
        grand_total=grand_total,
        upi_link=upi_link,
        items=item_rows,
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    return invoice


@app.get("/invoices", response_model=list[InvoiceOut], tags=["invoices"], dependencies=[Auth])
def list_invoices(db: Session = Depends(get_db)):
    return db.query(Invoice).order_by(Invoice.id).all()


@app.get("/invoices/{invoice_id}", response_model=InvoiceOut,
         tags=["invoices"], dependencies=[Auth])
def get_invoice(invoice_id: int, db: Session = Depends(get_db)):
    invoice = db.get(Invoice, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@app.get("/invoices/{invoice_id}/html", response_class=HTMLResponse,
         tags=["invoices"], dependencies=[Auth])
def invoice_html(invoice_id: int, db: Session = Depends(get_db)):
    """Printable invoice — open in a browser and Ctrl/Cmd+P to save as PDF."""
    inv = db.get(Invoice, invoice_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")

    e = html_lib.escape
    rows = "".join(
        f"<tr><td>{e(it.description)}</td><td>{e(it.hsn or '-')}</td>"
        f"<td>{it.quantity:g}</td><td>₹{it.rate:,.2f}</td><td>{it.gst_rate:g}%</td>"
        f"<td>₹{it.taxable_value:,.2f}</td><td>₹{it.total:,.2f}</td></tr>"
        for it in inv.items
    )
    seller_state = STATE_CODES.get(inv.seller_state_code, inv.seller_state_code)
    buyer_state = STATE_CODES.get(inv.buyer_state_code, inv.buyer_state_code)
    upi_block = (
        f'<p><strong>Pay via UPI:</strong> <a href="{e(inv.upi_link)}">{e(inv.upi_link)}</a></p>'
        if inv.upi_link else ""
    )
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>Invoice {e(inv.invoice_number)}</title>
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 760px; margin: 2rem auto; color: #111; }}
  table {{ width: 100%; border-collapse: collapse; margin: 1rem 0; }}
  th, td {{ border: 1px solid #ccc; padding: 6px 8px; text-align: left; font-size: 14px; }}
  .totals td {{ border: none; text-align: right; }}
  .grand {{ font-size: 18px; font-weight: 700; }}
  @media print {{ body {{ margin: 0; }} }}
</style></head><body>
<h1>Tax Invoice — {e(inv.invoice_number)}</h1>
<p>Date: {e(inv.issue_date)}</p>
<h3>Seller</h3>
<p>{e(inv.seller_name)}<br>{e(inv.seller_address or '')}<br>
GSTIN: {e(inv.seller_gstin or '—')} · State: {e(seller_state)} ({e(inv.seller_state_code)})</p>
<h3>Buyer</h3>
<p>{e(inv.buyer_name)}<br>
GSTIN: {e(inv.buyer_gstin or '—')} · State: {e(buyer_state)} ({e(inv.buyer_state_code)})</p>
<table><thead><tr><th>Item</th><th>HSN</th><th>Qty</th><th>Rate</th><th>GST</th>
<th>Taxable</th><th>Total</th></tr></thead><tbody>{rows}</tbody></table>
<table class="totals">
<tr><td>Subtotal:</td><td>₹{inv.subtotal:,.2f}</td></tr>
<tr><td>CGST:</td><td>₹{inv.cgst_amount:,.2f}</td></tr>
<tr><td>SGST:</td><td>₹{inv.sgst_amount:,.2f}</td></tr>
<tr><td>IGST:</td><td>₹{inv.igst_amount:,.2f}</td></tr>
<tr><td>Round off:</td><td>₹{inv.round_off:,.2f}</td></tr>
<tr><td class="grand">Grand Total:</td><td class="grand">₹{inv.grand_total:,.2f}</td></tr>
</table>
{upi_block}
<p><em>Generated by Bharat Bill API</em></p>
</body></html>"""
