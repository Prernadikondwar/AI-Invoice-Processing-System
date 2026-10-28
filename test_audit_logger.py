
from audit_logger import (
    check_duplicate,
    record_run,
    get_approved_invoiced_total,
    get_history,
)

invoice = {
    "invoice_number": "TEST-INV-001",
    "invoice_date": "20-10-2026",
    "vendor_name": "TechNova Hardware LLP",
    "po_number": "PO-2026-1009",
    "subtotal": 1000,
    "tax": 180,
    "total": 1180,
    "line_items": [],
}

# Check before saving.
print("Duplicate before saving:",
      check_duplicate(invoice["vendor_name"], invoice["invoice_number"]))

run_id = record_run(
    file_name="test_invoice.pdf",
    invoice=invoice,
    decision="Needs Review",
    reasons=["Test processing run."],
)

print("Saved run ID:", run_id)

# The same invoice identity should now be detected.
print("Duplicate after saving:",
      check_duplicate(invoice["vendor_name"], invoice["invoice_number"]))

print("Approved total for PO:",
      get_approved_invoiced_total(invoice["po_number"]))

print("History entries:", len(get_history()))
