import unittest

from decision_engine import decide_invoice
from po_matcher import match_invoice_to_po


class ApprovalFlowTests(unittest.TestCase):
    def test_matched_invoice_with_no_po_line_detail_can_be_approved(self):
        invoice = {
            "invoice_number": "DEMO-APPROVAL-TEST",
            "vendor_name": "Apex Office Supplies Pvt Ltd",
            "po_number": "PO-2026-1001",
            "invoice_date": "2026-10-28",
            "subtotal": 100000,
            "tax": 18000,
            "total": 118000,
            "currency": "INR",
            "items": [
                {
                    "description": "Office stationery and printer consumables",
                    "quantity": 10,
                    "unit_price": 10000,
                    "line_total": 100000,
                }
            ],
        }
        validation = {
            "status": "Passed",
            "failed_checks": [],
            "missing_information": [],
            "warnings": [],
        }

        matching = match_invoice_to_po(invoice)
        decision = decide_invoice(validation, matching)

        self.assertTrue(matching["po_found"])
        self.assertTrue(matching["vendor_verified"])
        self.assertEqual(matching["decision"], "Matched - Pending Validation")
        self.assertFalse(matching["reasons"])
        self.assertTrue(matching["warnings"])
        self.assertEqual(decision["decision"], "Approved")

    def test_po_mismatch_still_blocks_approval(self):
        invoice = {
            "invoice_number": "DEMO-APPROVAL-TEST",
            "vendor_name": "Apex Office Supplies Pvt Ltd",
            "po_number": "PO-2026-1001",
            "total": 200000,
            "currency": "INR",
        }
        validation = {
            "status": "Passed",
            "failed_checks": [],
            "missing_information": [],
            "warnings": [],
        }

        matching = match_invoice_to_po(invoice)
        decision = decide_invoice(validation, matching)

        self.assertTrue(matching["reasons"])
        self.assertEqual(decision["decision"], "Needs Review")


if __name__ == "__main__":
    unittest.main()
