"""GST helpers: state codes, GSTIN validation, tax split and UPI links.

GST logic (simplified, this is the rule every Indian invoice follows):
- Seller and buyer in the *same* state  -> intra-state supply.
  Tax is split equally into CGST (centre) + SGST (state).
- Seller and buyer in *different* states -> inter-state supply.
  The full tax is charged as IGST (integrated).
"""
from __future__ import annotations

import re
from decimal import ROUND_HALF_UP, Decimal
from urllib.parse import quote_plus

# GST state codes (first two digits of a GSTIN).
# Full list as per GSTN; major states covered plus all others commonly used.
STATE_CODES: dict[str, str] = {
    "01": "Jammu and Kashmir",
    "02": "Himachal Pradesh",
    "03": "Punjab",
    "04": "Chandigarh",
    "05": "Uttarakhand",
    "06": "Haryana",
    "07": "Delhi",
    "08": "Rajasthan",
    "09": "Uttar Pradesh",
    "10": "Bihar",
    "11": "Sikkim",
    "12": "Arunachal Pradesh",
    "13": "Nagaland",
    "14": "Manipur",
    "15": "Mizoram",
    "16": "Tripura",
    "17": "Meghalaya",
    "18": "Assam",
    "19": "West Bengal",
    "20": "Jharkhand",
    "21": "Odisha",
    "22": "Chhattisgarh",
    "23": "Madhya Pradesh",
    "24": "Gujarat",
    "26": "Dadra and Nagar Haveli and Daman and Diu",
    "27": "Maharashtra",
    "29": "Karnataka",
    "30": "Goa",
    "31": "Lakshadweep",
    "32": "Kerala",
    "33": "Tamil Nadu",
    "34": "Puducherry",
    "35": "Andaman and Nicobar Islands",
    "36": "Telangana",
    "37": "Andhra Pradesh",
    "38": "Ladakh",
}

# GST rates legally in use in India.
ALLOWED_GST_RATES = {0.0, 5.0, 12.0, 18.0, 28.0}

_GSTIN_RE = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")


def money(value: float | Decimal) -> float:
    """Round to 2 decimal places, half-up (standard billing practice)."""
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def validate_gstin(gstin: str | None) -> bool:
    """Return True if *gstin* looks like a valid GSTIN.

    Format: 15 chars — 2-digit state code, 10-char PAN, 1 entity code,
    'Z', 1 check character. E.g. 09ABCDE1234F1Z5 (Uttar Pradesh).
    This checks format and the state-code prefix; it does NOT verify
    the checksum or that the GSTIN is registered with GSTN.
    """
    if not gstin:
        return False
    gstin = gstin.strip().upper()
    if len(gstin) != 15 or not _GSTIN_RE.match(gstin):
        return False
    return gstin[:2] in STATE_CODES


def validate_state_code(state_code: str | None) -> bool:
    return bool(state_code) and state_code.strip() in STATE_CODES


def compute_item_tax(taxable_value: float, gst_rate: float, intra_state: bool) -> dict:
    """Compute CGST/SGST/IGST for one line item."""
    tax = money(taxable_value * gst_rate / 100)
    if intra_state:
        half = money(tax / 2)
        # If the split produces a paise remainder, put it in CGST so
        # cgst + sgst always equals the exact tax amount.
        cgst = money(tax - half)
        return {"cgst_amount": cgst, "sgst_amount": half, "igst_amount": 0.0, "tax_amount": tax}
    return {"cgst_amount": 0.0, "sgst_amount": 0.0, "igst_amount": tax, "tax_amount": tax}


def build_upi_link(upi_id: str, payee_name: str, amount: float, note: str = "") -> str:
    """Build a UPI intent string any UPI app (GPay/PhonePe/Paytm) understands.

    Example: upi://pay?pa=shop@okhdfcbank&pn=Sharma+Electronics&am=1180.00&cu=INR
    """
    link = (
        f"upi://pay?pa={quote_plus(upi_id)}"
        f"&pn={quote_plus(payee_name)}"
        f"&am={amount:.2f}&cu=INR"
    )
    if note:
        link += f"&tn={quote_plus(note)}"
    return link
