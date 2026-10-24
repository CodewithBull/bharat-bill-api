"""Seed the database with a demo shop, customers, products and an invoice.

Usage (with the API key env var set, or the dev default):
    python seed.py

It talks to the app in-process via FastAPI's TestClient, so no running
server is needed — it seeds the same SQLite database the API uses.
"""
from __future__ import annotations

import os

os.environ.setdefault("BHARAT_BILL_API_KEY", "dev-key-change-me")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from examples_data import CUSTOMERS, INVOICE, PRODUCTS  # noqa: E402

HEADERS = {"X-API-Key": os.environ["BHARAT_BILL_API_KEY"]}


def main() -> None:
    client = TestClient(app)
    for payload in CUSTOMERS:
        r = client.post("/customers", json=payload, headers=HEADERS)
        print("customer:", r.status_code, r.json().get("name"))
    for payload in PRODUCTS:
        r = client.post("/products", json=payload, headers=HEADERS)
        print("product:", r.status_code, r.json().get("name"))
    r = client.post("/invoices", json=INVOICE, headers=HEADERS)
    print("invoice:", r.status_code)
    if r.status_code == 201:
        inv = r.json()
        print(f"  {inv['invoice_number']}  grand total ₹{inv['grand_total']:,.2f}")
        print(f"  CGST ₹{inv['cgst_amount']}  SGST ₹{inv['sgst_amount']}  IGST ₹{inv['igst_amount']}")
        print(f"  UPI: {inv['upi_link']}")
        print(f"  Printable: GET /invoices/{inv['id']}/html")


if __name__ == "__main__":
    main()
