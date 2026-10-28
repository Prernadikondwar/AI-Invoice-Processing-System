
import pandas as pd
import re
from pathlib import Path


def normalize(value):
    """Normalize text for comparisons."""
    if value is None or pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value)).strip().casefold()


def to_number(value):
    """Convert a value to a number, or return None."""
    if value is None or pd.isna(value):
        return None

    try:
        cleaned = str(value).replace(",", "").replace("₹", "").strip()
        if not cleaned:
            return None
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def match_invoice_to_po(
    invoice,
    po_csv_path="data/purchase_orders.csv",
    vendors_csv_path="data/vendors (1).csv",
):
    """Compare an extracted invoice with PO and vendor records."""

    result = {
        "decision": "Needs Review",
        "reasons": [],
        "warnings": [],
        "comparison": {},
        "po_found": False,
        "vendor_verified": False,
    }

    # Check that the CSV files exist.
    if not Path(po_csv_path).exists():
        result["reasons"].append(f"PO file not found: {po_csv_path}")
        return result

    if not Path(vendors_csv_path).exists():
        result["reasons"].append(
            f"Vendor file not found: {vendors_csv_path}"
        )
        return result

    try:
        pos = pd.read_csv(po_csv_path)
        vendors = pd.read_csv(vendors_csv_path)
    except Exception as exc:
        result["reasons"].append(f"Could not read CSV files: {exc}")
        return result

    required_po = {
        "po_number", "vendor_id", "currency",
        "po_total_incl_tax", "remaining_balance",
        "tolerance_pct", "status"
    }
    required_vendor = {
        "vendor_id", "vendor_name", "status", "currency"
    }

    if not required_po.issubset(pos.columns):
        result["reasons"].append("PO CSV is missing required columns.")
        return result

    if not required_vendor.issubset(vendors.columns):
        result["reasons"].append(
            "Vendor CSV is missing required columns."
        )
        return result

    po_number = normalize(invoice.get("po_number"))
    invoice_vendor = normalize(invoice.get("vendor_name"))
    invoice_total = to_number(invoice.get("total"))
    invoice_currency = normalize(invoice.get("currency") or "INR")

    if not po_number:
        result["reasons"].append("Invoice PO number is missing.")
        return result

    matching_pos = pos[
        pos["po_number"].apply(normalize) == po_number
    ]

    if len(matching_pos) == 0:
        result["reasons"].append(
            f"PO {po_number} was not found."
        )
        return result

    if len(matching_pos) > 1:
        result["reasons"].append(
            f"Multiple records found for PO {po_number}; manual review required."
        )
        return result

    po = matching_pos.iloc[0]
    result["po_found"] = True

    vendor_id = normalize(po["vendor_id"])
    vendor_rows = vendors[
        vendors["vendor_id"].apply(normalize) == vendor_id
    ]

    if len(vendor_rows) != 1:
        result["reasons"].append(
            "PO vendor record is missing or ambiguous."
        )
        return result

    vendor = vendor_rows.iloc[0]
    po_vendor_name = normalize(vendor["vendor_name"])

    vendor_matches = (
        bool(invoice_vendor)
        and invoice_vendor == po_vendor_name
    )

    result["vendor_verified"] = vendor_matches

    result["comparison"] = {
        "invoice_po": po_number,
        "po_vendor": vendor["vendor_name"],
        "invoice_vendor": invoice.get("vendor_name"),
        "vendor_match": vendor_matches,
        "invoice_total": invoice_total,
        "po_total": to_number(po["po_total_incl_tax"]),
        "remaining_balance": to_number(po["remaining_balance"]),
        "tolerance_pct": to_number(po["tolerance_pct"]),
        "po_status": str(po["status"]),
    }

    if not invoice_vendor:
        result["reasons"].append("Invoice vendor name is missing.")
    elif not vendor_matches:
        result["reasons"].append(
            "Invoice vendor does not match the vendor assigned to the PO."
        )

    if normalize(vendor["status"]) != "approved":
        result["reasons"].append("Vendor is not marked APPROVED.")

    if invoice_currency != normalize(po["currency"]):
        result["reasons"].append(
            "Invoice currency does not match the PO currency."
        )

    if normalize(vendor["currency"]) != invoice_currency:
        result["reasons"].append(
            "Invoice currency does not match the vendor currency."
        )

    if invoice_total is None:
        result["reasons"].append(
            "Invoice total is missing or not numeric."
        )
    elif invoice_total <= 0:
        result["reasons"].append(
            "Invoice total must be greater than zero."
        )

    po_status = normalize(po["status"])
    if po_status != "open" and po_status != "partially_invoiced":
        result["reasons"].append(
            f"PO status is {po['status']}; verify that invoicing is permitted."
        )

    remaining = to_number(po["remaining_balance"])
    tolerance_pct = to_number(po["tolerance_pct"])

    if invoice_total is not None and remaining is not None:
        allowed_amount = remaining

        if tolerance_pct is not None and tolerance_pct >= 0:
            allowed_amount = remaining * (1 + tolerance_pct / 100)

        difference = invoice_total - remaining
        result["comparison"]["difference_vs_remaining"] = difference
        result["comparison"]["allowed_amount"] = allowed_amount

        if invoice_total > allowed_amount + 0.01:
            result["reasons"].append(
                f"Invoice exceeds the remaining PO balance by "
                f"₹{difference:,.2f}; configured tolerance was applied."
            )

    # This CSV contains PO-level descriptions and totals, not detailed
    # PO line-item quantities and unit prices. Those need a separate
    # line-item source for full item-by-item matching.
    result["warnings"].append(
        "Detailed PO line-item quantity and unit-price comparison "
        "is not available in the supplied PO CSV."
    )

    result["decision"] = (
        "Matched - Pending Validation"
        if not result["reasons"]
        else "Needs Review"
    )

    return result
