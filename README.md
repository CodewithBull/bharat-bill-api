# Bharat Bill API 🇮🇳

A **GST billing API for small Indian shops and freelancers** — built with FastAPI.

Create GST-correct invoices from a simple JSON payload. The API works out the
tax for you: **CGST + SGST** for sales within your state, **IGST** for sales
outside it, generates a **UPI payment link** for the bill, and gives you a
**printable HTML invoice** you can hand to the customer.

> Example shop used throughout: *Sharma Electronics, Main Market, Gajraula,
> Uttar Pradesh* — the kind of shop that today writes bills in a register,
>uses a generic billing app that gets GST wrong, or pays for heavy software
>it doesn't need.

## Why this exists

Small shops and freelancers in India have a very specific billing problem:

- GST has to be split differently for local vs out-of-state sales, and
  getting it wrong shows up later when filing returns.
- Customers expect a UPI QR / link on the bill — most of India pays that way.
- Existing billing software is either expensive, bloated, or not API-first,
  so it can't plug into a shop's own website / WhatsApp ordering flow.

Bharat Bill API is the small, hackable, API-first version of that.

## Features

- ✅ Create / list / get **invoices** with line items (HSN, quantity, rate, GST rate)
- ✅ **Automatic GST split** — intra-state → CGST + SGST (half each), inter-state → IGST
- ✅ Totals with **round-off** to the nearest rupee and a grand total
- ✅ **UPI payment string** on every invoice (`upi://pay?pa=...&pn=...&am=...&cu=INR`)
- ✅ **Printable HTML invoice** — open in a browser, print / save as PDF
- ✅ Simple **customers** and **products** CRUD
- ✅ **GSTIN format validation** and a lookup of all GST **state codes**
- ✅ **API-key auth** (`X-API-Key` header), SQLite storage, interactive Swagger docs
- ✅ Test suite (pytest + FastAPI TestClient) covering the GST math

## How the GST split works

GST state codes are the first two digits of a GSTIN — `09` = Uttar Pradesh,
`07` = Delhi, `27` = Maharashtra, and so on (see `GET /states`).

| Sale | Example | Tax charged |
| --- | --- | --- |
| Intra-state (seller state = buyer state) | UP shop → UP customer | CGST 9% + SGST 9% on an 18% item |
| Inter-state (seller state ≠ buyer state) | UP shop → Delhi customer | IGST 18% |

Tax is calculated per line item on `quantity × rate`, rounded to the paise
(half-up). Invoice totals are the sum of the line items, then rounded to the
nearest rupee with the difference reported as `round_off`.

> This is a developer tool, not a CA. It validates GSTIN *format* and state
> codes, but does not verify a GSTIN against GSTN or file your returns.

## Quickstart

```bash
git clone <this repo> && cd bharat-bill-api

python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Optional: copy .env.example and set your own key
export BHARAT_BILL_API_KEY=dev-key-change-me        # this is the default dev key

uvicorn app.main:app --reload
```

- API: http://127.0.0.1:8000
- **Swagger docs: http://127.0.0.1:8000/docs** — click *Authorize*, or just
  send the header below with every request.
- Health check (no key needed): http://127.0.0.1:8000/health

Seed demo data (a Gajraula electronics shop, customers, products, one invoice):

```bash
python seed.py
```

Run the tests:

```bash
pytest -q
```

## API overview

All endpoints except `/health` and `/docs` need the header
`X-API-Key: <BHARAT_BILL_API_KEY>`.

| Method | Endpoint | What it does |
| --- | --- | --- |
| GET | `/health` | Liveness check |
| GET | `/states` | GST state code → state name |
| GET | `/validate/gstin/{gstin}` | Check a GSTIN's format + state |
| POST / GET | `/customers`, `/customers/{id}` | Customer CRUD (create/list/get) |
| POST / GET | `/products`, `/products/{id}` | Product CRUD (create/list/get) |
| POST / GET | `/invoices`, `/invoices/{id}` | Create / list / get invoices |
| GET | `/invoices/{id}/html` | Printable HTML invoice |

## curl examples

Health:

```bash
curl http://127.0.0.1:8000/health
```

Create a customer:

```bash
curl -X POST http://127.0.0.1:8000/customers \
  -H "X-API-Key: dev-key-change-me" -H "Content-Type: application/json" \
  -d '{"name":"Rahul Verma","gstin":"09FGHIJ5678K1Z3","state_code":"09","phone":"9876543210"}'
```

Create a product:

```bash
curl -X POST http://127.0.0.1:8000/products \
  -H "X-API-Key: dev-key-change-me" -H "Content-Type: application/json" \
  -d '{"name":"Ceiling Fan 1200mm","hsn":"8414","rate":2450,"gst_rate":18}'
```

Create an invoice (also in `examples/sample_invoice.json`):

```bash
curl -X POST http://127.0.0.1:8000/invoices \
  -H "X-API-Key: dev-key-change-me" -H "Content-Type: application/json" \
  -d @examples/sample_invoice.json
```

List and get invoices:

```bash
curl http://127.0.0.1:8000/invoices -H "X-API-Key: dev-key-change-me"
curl http://127.0.0.1:8000/invoices/1 -H "X-API-Key: dev-key-change-me"
```

Printable invoice (open in a browser):

```bash
curl http://127.0.0.1:8000/invoices/1/html -H "X-API-Key: dev-key-change-me"
```

Validate a GSTIN and list state codes:

```bash
curl http://127.0.0.1:8000/validate/gstin/09ABCDE1234F1Z5 -H "X-API-Key: dev-key-change-me"
curl http://127.0.0.1:8000/states -H "X-API-Key: dev-key-change-me"
```

## Sample invoice

Request:

```json
{
  "seller_name": "Sharma Electronics",
  "seller_gstin": "09ABCDE1234F1Z5",
  "seller_state_code": "09",
  "seller_upi_id": "sharmaelectronics@okhdfcbank",
  "seller_address": "Main Market, Gajraula, Uttar Pradesh 244235",
  "buyer_name": "Rahul Verma",
  "buyer_gstin": "09FGHIJ5678K1Z3",
  "buyer_state_code": "09",
  "items": [
    {"description": "Ceiling Fan 1200mm", "hsn": "8414", "quantity": 1, "rate": 2450, "gst_rate": 18},
    {"description": "LED Bulb 9W (pack of 4)", "hsn": "8539", "quantity": 2, "rate": 399, "gst_rate": 12}
  ]
}
```

Response (trimmed): subtotal ₹3,248, tax ₹536.76 split as CGST ₹268.38 +
SGST ₹268.38 (same-state sale), grand total ₹3,785 (₹3,784.76 rounded), and

```
upi://pay?pa=sharmaelectronics%40okhdfcbank&pn=Sharma+Electronics&am=3785.00&cu=INR&tn=Invoice+INV-2026-0001
```

For an inter-state sale the *same* kind of bill charges the full tax as
IGST instead of CGST+SGST — see `examples/sample_invoice_interstate.json`
(UP shop → Delhi buyer). No other change needed — that's the point.

## Project structure

```
bharat-bill-api/
├── app/
│   ├── main.py        # FastAPI app, routes, printable invoice HTML
│   ├── models.py      # SQLAlchemy: Customer, Product, Invoice, InvoiceItem
│   ├── schemas.py     # Pydantic request/response schemas + validation
│   ├── gst.py         # State codes, GSTIN check, GST split, UPI link builder
│   ├── auth.py        # X-API-Key auth (BHARAT_BILL_API_KEY)
│   └── database.py    # SQLite / SQLAlchemy setup
├── tests/
│   ├── conftest.py    # Isolated temp DB + known test API key
│   └── test_api.py    # GST split, totals, auth, UPI, full invoice flow
├── examples/
│   ├── sample_invoice.json            # Intra-state (UP -> UP)
│   └── sample_invoice_interstate.json # Inter-state (UP -> Delhi)
├── examples_data.py   # Demo shop / customers / products used by seed.py
├── seed.py            # Seed demo data in-process (no server needed)
├── requirements.txt
├── .env.example
└── LICENSE            # MIT
```

## Roadmap

- [ ] PDF invoice generation (in addition to printable HTML)
- [ ] UPI QR code image endpoint for the invoice
- [ ] Credit / debit notes and invoice cancellation
- [ ] GSTR-1 friendly CSV export
- [ ] Discounts (per-item and bill-level) and multiple GSTINs per seller
- [ ] Docker image + deployment guide

## License

MIT — see [LICENSE](LICENSE).
