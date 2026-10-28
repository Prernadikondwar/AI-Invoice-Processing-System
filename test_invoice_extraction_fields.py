import io
import unittest
from unittest.mock import patch

import pytesseract

import invoice_extractor
from data_validator import validate_invoice


class InvoiceExtractionTests(unittest.TestCase):
    def test_extract_totals_from_inline_and_following_line_values(self):
        text = """
        Subtotal: Rs. 1,00,000.00
        Total GST
        18,000.00
        Grand Total ₹ 1,18,000.00
        """

        self.assertEqual(
            invoice_extractor.extract_totals(text),
            {
                "subtotal": 100000.0,
                "tax": 18000.0,
                "total": 118000.0,
            },
        )

    def test_validate_extractor_line_item_schema(self):
        invoice = {
            "invoice_number": "APX-2026-0231",
            "invoice_date": "2026-10-20",
            "vendor_name": "Apex Office Supplies Pvt Ltd",
            "subtotal": 100000,
            "tax": 18000,
            "total": 118000,
            "items": [
                {
                    "description": "Paper",
                    "quantity": 10,
                    "unit_price": 10000,
                    "line_total": 100000,
                }
            ],
        }

        report = validate_invoice(invoice)

        self.assertIn(
            "Line-item quantities and prices are valid.",
            report["passed_checks"],
        )
        self.assertIn(
            "Calculated subtotal matches the invoice.",
            report["passed_checks"],
        )

    def test_ocr_fallback_fills_fields_missing_from_partial_text(self):
        digital_text = (
            "Invoice Number: APX-2026-0231\n"
            "Vendor: Apex Office Supplies Pvt Ltd\n"
            "PO Number: PO-2026-1001"
        )
        ocr_text = """
        Invoice Number: APX-2026-0231
        Vendor: Apex Office Supplies Pvt Ltd
        PO Number: PO-2026-1001
        Invoice Date: 20/10/2026
        Subtotal: 100000.00
        Total GST: 18000.00
        Grand Total: 118000.00
        Paper 10 10000.00 100000.00
        """
        with (
            patch.object(
                invoice_extractor,
                "extract_text_from_pdf",
                return_value=(digital_text, "PyMuPDF"),
            ),
            patch.object(
                invoice_extractor,
                "extract_ocr_text_from_pdf",
                return_value=ocr_text,
            ),
        ):
            result = invoice_extractor.extract_invoice(io.BytesIO(b"pdf"))

        self.assertTrue(result["success"])
        self.assertEqual(
            result["extraction_method"],
            "PyMuPDF + Tesseract OCR",
        )
        self.assertEqual(result["fields"]["invoice_date"], "2026-10-20")
        self.assertEqual(result["fields"]["subtotal"], 100000.0)
        self.assertEqual(result["fields"]["tax"], 18000.0)
        self.assertEqual(result["fields"]["total"], 118000.0)
        self.assertEqual(len(result["fields"]["items"]), 1)

    def test_missing_tesseract_keeps_digital_fields_and_warns(self):
        digital_text = (
            "Invoice Number: APX-2026-0231\n"
            "Vendor: Apex Office Supplies Pvt Ltd\n"
            "PO Number: PO-2026-1001"
        )
        with (
            patch.object(
                invoice_extractor,
                "extract_text_from_pdf",
                return_value=(digital_text, "PyMuPDF"),
            ),
            patch.object(
                invoice_extractor,
                "extract_ocr_text_from_pdf",
                side_effect=pytesseract.TesseractNotFoundError(),
            ),
        ):
            result = invoice_extractor.extract_invoice(io.BytesIO(b"pdf"))

        self.assertTrue(result["success"])
        self.assertEqual(
            result["fields"]["invoice_number"],
            "APX-2026-0231",
        )
        self.assertTrue(
            any("Tesseract" in warning for warning in result["warnings"])
        )


if __name__ == "__main__":
    unittest.main()
