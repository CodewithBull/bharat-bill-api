"""End-to-end tests for Bharat Bill API."""
from app.gst import build_upi_link, validate_gstin
from tests.conftest import HEADERS

SELLER_UP = {
    "seller_name": "Sharma Electronics",
    "seller_gstin": "09ABCDE1234F1Z5",
    "seller_state_code": "09",  # Uttar Pradesh (Gajraula)
    "seller_upi_id": "sharmaelectronics@okhdfcbank",
    "seller_address": "Main Market, Gajraula, Uttar Pradesh 244235",
}


def make_invoice(client, buyer_state="09", items=None, **overrides):
    payload = {
        **SELLER_UP,
        "buyer_name": "Rahul Verma",
        "buyer_state_code": buyer_state,
        "items": items or [
            {"description": "Ceiling Fan 1200mm", "hsn": "8414", "quantity": 1, "rate": 1000, "gst_rate": 18}
        ],
        **overrides,
    }
    return client.post("/invoices", json=payload, headers=HEADERS)


# ------------------------------------------------------------------- basics
def test_health_needs_no_auth(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_auth_failure(client):
    assert client.get("/invoices").status_code == 403
    assert client.get("/invoices", headers={"X-API-Key": "wrong"}).status_code == 403
    r = client.post("/invoices", json={}, headers={"X-API-Key": "wrong"})
    assert r.status_code == 403


def test_gstin_validation_helper():
    assert validate_gstin("09ABCDE1234F1Z5")
    assert validate_gstin("27AAAPL1234C1Z6")  # Maharashtra
    assert not validate_gstin("09ABCDE1234F1Z")     # too short
    assert not validate_gstin("99ABCDE1234F1Z5")    # bogus state code
    assert not validate_gstin("not-a-gstin")
    assert not validate_gstin(None)


def test_invalid_gstin_rejected_on_invoice(client):
    r = make_invoice(client, seller_gstin="BAD")
    assert r.status_code == 422


def test_invalid_state_code_rejected(client):
    r = make_invoice(client, buyer_state="99")
    assert r.status_code == 422


# ---------------------------------------------------------------- GST split
def test_intra_state_split_cgst_sgst(client):
    r = make_invoice(client, buyer_state="09")  # UP -> UP
    assert r.status_code == 201, r.text
    inv = r.json()
    assert inv["subtotal"] == 1000.0
    assert inv["cgst_amount"] == 90.0
    assert inv["sgst_amount"] == 90.0
    assert inv["igst_amount"] == 0.0
    assert inv["tax_amount"] == 180.0
    assert inv["grand_total"] == 1180.0
    assert inv["items"][0]["cgst_amount"] == 90.0


def test_inter_state_igst(client):
    r = make_invoice(client, buyer_state="07")  # UP -> Delhi
    assert r.status_code == 201, r.text
    inv = r.json()
    assert inv["cgst_amount"] == 0.0
    assert inv["sgst_amount"] == 0.0
    assert inv["igst_amount"] == 180.0
    assert inv["grand_total"] == 1180.0


def test_totals_multiple_items_and_round_off(client):
    items = [
        {"description": "LED Bulb 9W", "hsn": "8539", "quantity": 3, "rate": 99.50, "gst_rate": 12},
        {"description": "Extension Board", "hsn": "8536", "quantity": 1, "rate": 499, "gst_rate": 18},
    ]
    r = make_invoice(client, buyer_state="09", items=items)
    assert r.status_code == 201, r.text
    inv = r.json()
    # taxable: 3*99.50=298.50 (@12% = 35.82) + 499 (@18% = 89.82) = 797.50 + 125.64
    assert inv["subtotal"] == 797.50
    assert inv["tax_amount"] == 125.64
    assert inv["cgst_amount"] == 62.82
    assert inv["sgst_amount"] == 62.82
    # 923.14 rounds to 923, round-off -0.14
    assert inv["grand_total"] == 923.0
    assert inv["round_off"] == -0.14


# --------------------------------------------------------------------- UPI
def test_upi_string_on_invoice(client):
    r = make_invoice(client, buyer_state="09")
    inv = r.json()
    assert inv["upi_link"].startswith("upi://pay?pa=sharmaelectronics%40okhdfcbank")
    assert "pn=Sharma+Electronics" in inv["upi_link"]
    assert "am=1180.00" in inv["upi_link"]
    assert "cu=INR" in inv["upi_link"]


def test_upi_builder_direct():
    link = build_upi_link("shop@okaxis", "Gupta Kirana Store", 250.5)
    assert link == "upi://pay?pa=shop%40okaxis&pn=Gupta+Kirana+Store&am=250.50&cu=INR"


def test_no_upi_link_without_upi_id(client):
    r = make_invoice(client, buyer_state="09", seller_upi_id=None)
    assert r.status_code == 201
    assert r.json()["upi_link"] is None


# -------------------------------------------------------------- full flow
def test_invoice_creation_flow(client):
    # customer
    r = client.post("/customers", json={
        "name": "Rahul Verma", "gstin": "09FGHIJ5678K1Z3",
        "state_code": "09", "phone": "9876543210",
    }, headers=HEADERS)
    assert r.status_code == 201, r.text
    customer_id = r.json()["id"]

    # product
    r = client.post("/products", json={
        "name": "Ceiling Fan 1200mm", "hsn": "8414", "rate": 1000, "gst_rate": 18,
    }, headers=HEADERS)
    assert r.status_code == 201
    assert client.get("/products", headers=HEADERS).json()[0]["name"] == "Ceiling Fan 1200mm"

    # invoice linked to the customer
    r = make_invoice(client, customer_id=customer_id)
    assert r.status_code == 201, r.text
    invoice_id = r.json()["id"]
    assert r.json()["invoice_number"].startswith("INV-")

    # list + get
    assert len(client.get("/invoices", headers=HEADERS).json()) == 1
    got = client.get(f"/invoices/{invoice_id}", headers=HEADERS)
    assert got.status_code == 200
    assert got.json()["buyer_name"] == "Rahul Verma"
    assert client.get("/invoices/9999", headers=HEADERS).status_code == 404

    # printable HTML
    r = client.get(f"/invoices/{invoice_id}/html", headers=HEADERS)
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "Sharma Electronics" in r.text
    assert "Tax Invoice" in r.text
    assert "1,180.00" in r.text


def test_states_and_gstin_endpoints(client):
    states = client.get("/states", headers=HEADERS).json()
    assert states["09"] == "Uttar Pradesh"
    assert states["27"] == "Maharashtra"
    r = client.get("/validate/gstin/09ABCDE1234F1Z5", headers=HEADERS)
    assert r.json() == {
        "gstin": "09ABCDE1234F1Z5", "valid_format": True,
        "state_code": "09", "state": "Uttar Pradesh",
    }
