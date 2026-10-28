
from pprint import pprint
from po_matcher import match_invoice_to_po

# Example invoice matching the structure of your CSV.
# Replace these values with details extracted from an actual invoice.
invoice = {
    "invoice_number": "TEST-1001",
    "vendor_name": "Metro Cleaning Services",
    "po_number": "PO-2026-1007",
    "total": 141600,
    "currency": "INR",
}

result = match_invoice_to_po(invoice)
pprint(result)
