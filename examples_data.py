"""Demo data used by seed.py — a small electronics shop in Gajraula, UP."""

CUSTOMERS = [
    {"name": "Rahul Verma", "gstin": "09FGHIJ5678K1Z3", "state_code": "09",
     "phone": "9876543210", "address": "Station Road, Gajraula, UP 244235"},
    {"name": "Delhi Traders", "gstin": "07ABCDE1234F1Z5", "state_code": "07",
     "phone": "9811002233", "address": "Chandni Chowk, Delhi 110006"},
]

PRODUCTS = [
    {"name": "Ceiling Fan 1200mm", "hsn": "8414", "rate": 2450, "gst_rate": 18, "unit": "pcs"},
    {"name": "LED Bulb 9W (pack of 4)", "hsn": "8539", "rate": 399, "gst_rate": 12, "unit": "pack"},
    {"name": "Copper Wire 1.5 sq mm, 90m", "hsn": "8544", "rate": 1850, "gst_rate": 18, "unit": "coil"},
    {"name": "Mixer Grinder 750W", "hsn": "8509", "rate": 3200, "gst_rate": 18, "unit": "pcs"},
]

INVOICE = {
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
        {"description": "LED Bulb 9W (pack of 4)", "hsn": "8539", "quantity": 2, "rate": 399, "gst_rate": 12},
    ],
}
