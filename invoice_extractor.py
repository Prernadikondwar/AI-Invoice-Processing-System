
"""
Invoice Extractor
-----------------
Extracts invoice information from digital or scanned PDFs.

Dependencies:
    pip install pymupdf pytesseract pillow

Tesseract OCR must also be installed on Windows.
"""

import io
import re
import os
from datetime import datetime

import fitz  # PyMuPDF
import pytesseract
from PIL import Image


# ---------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------

# Update this path if Tesseract is installed elsewhere.
TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

if os.path.exists(TESSERACT_PATH):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH


# ---------------------------------------------------------
# GENERAL HELPERS
# ---------------------------------------------------------

def clean_text(text):
    """Normalize whitespace in extracted text."""
    if not text:
        return ""

    text = text.replace("\u00a0", " ")
    text = text.replace("\u20b9", "Rs ")
    text = re.sub(r"[ \t]+", " ", text)

    return text.strip()


def parse_amount(value):
    """
    Convert formatted currency values to float.

    Examples:
        '₹94,400.00' -> 94400.00
        'Rs. 10,000' -> 10000.00
        '(500.00)' -> -500.00
    """
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return float(value)

    value = str(value).strip()

    if not value:
        return None

    negative = value.startswith("(") and value.endswith(")")

    value = value.strip("()")
    value = re.sub(r"(?i)\b(?:INR|Rs\.?|USD|EUR)\b", "", value)
    value = value.replace("₹", "")
    value = value.replace("$", "")
    value = value.replace("€", "")
    value = value.replace(",", "")
    value = value.replace(" ", "")

    match = re.search(r"-?\d+(?:\.\d+)?", value)

    if not match:
        return None

    try:
        number = float(match.group())

        if negative:
            number = -abs(number)

        return number

    except (ValueError, TypeError):
        return None


def find_first(patterns, text, flags=re.IGNORECASE | re.MULTILINE):
    """Return the first non-empty regex capture."""
    for pattern in patterns:
        match = re.search(pattern, text, flags)

        if match:
            value = match.group(1).strip(" \t:-")

            if value:
                return value

    return None


# ---------------------------------------------------------
# PDF TEXT EXTRACTION
# ---------------------------------------------------------

def extract_text_from_pdf(pdf_bytes):
    """
    Extract text from a PDF.

    Returns:
        text, extraction_method
    """
    document = fitz.open(
        stream=pdf_bytes,
        filetype="pdf"
    )

    try:
        page_texts = []

        for page in document:
            page_texts.append(page.get_text("text"))

        text = "\n".join(page_texts).strip()

        # A scanned PDF may contain no selectable text.
        # Use OCR if digital extraction produces too little text.
        if len(re.sub(r"\s+", "", text)) >= 30:
            return text, "PyMuPDF"

        ocr_text = extract_ocr_text_from_pdf(pdf_bytes)

        if len(re.sub(r"\s+", "", ocr_text)) > len(
            re.sub(r"\s+", "", text)
        ):
            return ocr_text, "Tesseract OCR"

        return text, "PyMuPDF"

    finally:
        document.close()


def extract_ocr_text_from_pdf(pdf_bytes):
    """Run OCR across every page, including pages with partial digital text."""
    document = fitz.open(stream=pdf_bytes, filetype="pdf")

    try:
        ocr_pages = []

        for page in document:
            pix = page.get_pixmap(
                matrix=fitz.Matrix(2, 2),
                alpha=False
            )
            image = Image.open(io.BytesIO(pix.tobytes("png")))
            ocr_pages.append(
                pytesseract.image_to_string(image, config="--psm 3")
            )

        return "\n".join(ocr_pages).strip()
    finally:
        document.close()


# ---------------------------------------------------------
# INVOICE FIELD EXTRACTION
# ---------------------------------------------------------

def extract_invoice_number(text):
    patterns = [
        r"(?im)^\s*(?:invoice|inv)\s*(?:number|no\.?|#|id)\s*[:#\-]?\s*([A-Z0-9][A-Z0-9/_-]*)",
        r"(?im)^\s*invoice\s*[:#\-]\s*([A-Z0-9][A-Z0-9/_-]*)",
        r"(?im)^\s*bill\s*(?:number|no\.?|#)\s*[:#\-]?\s*([A-Z0-9][A-Z0-9/_-]*)",
    ]

    return find_first(patterns, text)


def extract_po_number(text):
    patterns = [
        r"(?im)\b(?:purchase\s+order|PO)\s*(?:number|no\.?|#|ref(?:erence)?)?\s*[:#\-]?\s*(PO[-/_]?[A-Z0-9][A-Z0-9/_-]*)\b",
        r"(?i)\b(PO-\d{4}-\d+)\b",
    ]

    value = find_first(patterns, text)

    return value.strip() if value else None


def extract_vendor(text):
    """
    Extract vendor from common labeled fields.

    Does not assume that the first line is the vendor.
    """
    patterns = [
        r"(?im)^\s*(?:Vendor|Supplier)(?:\s+Name)?\s*[:\-]\s*(.+?)\s*$",
        r"(?im)^\s*(?:Billed\s+By|Sold\s+By|Issued\s+By)\s*[:\-]\s*(.+?)\s*$",
        r"(?im)^\s*From\s*[:\-]\s*(.+?)\s*$",
    ]

    value = find_first(patterns, text)

    if value:
        value = re.sub(
            r"\s+(?:GSTIN|GST\s*IN|PAN)\s*:.*$",
            "",
            value,
            flags=re.IGNORECASE
        ).strip()

        if value:
            return value

    # Try a labeled company name on the line following a vendor label.
    lines = [line.strip() for line in text.splitlines()]

    for index, line in enumerate(lines[:-1]):
        if re.fullmatch(
            r"(?:vendor|supplier|billed by|sold by|issued by)",
            line,
            flags=re.IGNORECASE
        ):
            candidate = lines[index + 1]

            if (
                candidate
                and not re.search(
                    r"invoice|date|gstin|email|phone|address",
                    candidate,
                    re.IGNORECASE
                )
                and not re.fullmatch(r"[\d\s/.-]+", candidate)
            ):
                return candidate

    return None


def extract_invoice_date(text):
    patterns = [
        r"(?im)\b(?:invoice\s+date|bill\s+date|date\s+of\s+invoice)\s*[:\-]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        r"(?im)\b(?:invoice\s+date|bill\s+date|date\s+of\s+invoice)\s*[:\-]?\s*(\d{4}-\d{2}-\d{2})",
        r"(?im)\b(?:invoice\s+date|bill\s+date|date\s+of\s+invoice)\s*[:\-]?\s*(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})",
    ]

    value = find_first(patterns, text)

    if not value:
        return None

    formats = [
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%m/%d/%Y",
        "%m-%d-%Y",
        "%Y-%m-%d",
        "%d %b %Y",
        "%d %B %Y",
    ]

    for date_format in formats:
        try:
            parsed = datetime.strptime(value, date_format)
            return parsed.strftime("%Y-%m-%d")
        except ValueError:
            continue

    # Preserve an unrecognized date for manual review.
    return value


def extract_amount_field(text, labels):
    """Extract an amount written beside a label or on the following line."""
    amount_pattern = r"-?\(?\d[\d,]*(?:\.\d{1,2})?\)?"
    standalone_amount = re.compile(
        r"^\s*(?:(?:INR|Rs\.?|₹)\s*)?"
        + f"({amount_pattern})"
        + r"(?:\s*(?:INR|Rs\.?|₹))?\s*$",
        re.IGNORECASE,
    )
    amount_after_label = re.compile(
        r"^\s*[:\-]?\s*(?:(?:INR|Rs\.?|₹)\s*)?"
        + f"({amount_pattern})",
        re.IGNORECASE,
    )

    for label in labels:
        label_pattern = re.compile(
            r"(?<!\w)(?:"
            + label
            + r")(?!\w)",
            re.IGNORECASE,
        )

        lines = text.splitlines()

        for index, line in enumerate(lines):
            match = label_pattern.search(line)

            if match:
                inline_amount = amount_after_label.match(line[match.end():])
                amount = (
                    parse_amount(inline_amount.group(1))
                    if inline_amount
                    else None
                )
                if amount is not None:
                    return amount

                if index + 1 < len(lines):
                    next_line = standalone_amount.fullmatch(lines[index + 1])
                    if next_line:
                        return parse_amount(next_line.group(1))

    return None


def extract_totals(text):
    """Extract subtotal, tax and total without guessing missing values."""
    subtotal = extract_amount_field(
        text,
        [
            r"sub\s*total",
            r"subtotal",
            r"taxable\s+value",
            r"amount\s+before\s+tax",
        ]
    )

    total = extract_amount_field(
        text,
        [
            r"grand\s+total",
            r"total\s+amount",
            r"invoice\s+total",
            r"net\s+payable",
            r"amount\s+payable",
            r"total\s+due",
            r"total",
        ]
    )

    # Exclude CGST/SGST/IGST component lines from the generic tax match.
    tax = extract_amount_field(
        text,
        [
            r"total\s+GST",
            r"total\s+tax",
            r"tax\s+amount",
            r"GST\s+amount",
        ]
    )

    if tax is None:
        cgst = extract_amount_field(text, [r"CGST"])
        sgst = extract_amount_field(text, [r"SGST"])
        igst = extract_amount_field(text, [r"IGST"])

        components = [
            amount for amount in (cgst, sgst, igst)
            if amount is not None
        ]

        if components:
            tax = sum(components)

    return {
        "subtotal": subtotal,
        "tax": tax,
        "total": total,
    }


# ---------------------------------------------------------
# LINE ITEM EXTRACTION
# ---------------------------------------------------------

def extract_line_items(text):
    """
    Extract simple table rows.

    Supported examples:
        Laptop 5 40000 200000
        Laptop 5 40,000.00 200,000.00

    Complex table layouts may require layout-specific parsing.
    """
    items = []

    number = r"\d[\d,]*(?:\.\d{1,2})?"

    pattern = re.compile(
        rf"^(.+?)\s+"
        rf"(\d+(?:\.\d+)?)\s+"
        rf"({number})\s+"
        rf"({number})\s*$"
    )

    for line in text.splitlines():
        line = line.strip()

        if not line:
            continue

        if re.search(
            r"\b(description|item description|quantity|qty|unit price|amount|grand total)\b",
            line,
            re.IGNORECASE
        ):
            continue

        match = pattern.match(line)

        if not match:
            continue

        description = match.group(1).strip()
        quantity = float(match.group(2))
        unit_price = parse_amount(match.group(3))
        line_total = parse_amount(match.group(4))

        if (
            description
            and quantity > 0
            and unit_price is not None
            and line_total is not None
        ):
            items.append({
                "description": description,
                "quantity": quantity,
                "unit_price": unit_price,
                "line_total": line_total,
            })

    return items


def extract_invoice_fields(text):
    """Extract the fields used by validation and purchase-order matching."""
    fields = {
        "invoice_number": extract_invoice_number(text),
        "vendor_name": extract_vendor(text),
        "po_number": extract_po_number(text),
        "invoice_date": extract_invoice_date(text),
    }
    fields.update(extract_totals(text))
    fields["items"] = extract_line_items(text)
    return fields


# ---------------------------------------------------------
# MAIN EXTRACTION FUNCTION
# ---------------------------------------------------------

def extract_invoice(uploaded_file):
    """
    Accept a Streamlit UploadedFile or a filesystem PDF path.

    Returns a dictionary compatible with the Streamlit UI.
    """
    try:
        if isinstance(uploaded_file, (str, os.PathLike)):
            with open(uploaded_file, "rb") as file:
                pdf_bytes = file.read()
        else:
            # Streamlit UploadedFile supports getvalue().
            if hasattr(uploaded_file, "getvalue"):
                pdf_bytes = uploaded_file.getvalue()
            else:
                pdf_bytes = uploaded_file.read()

        if not pdf_bytes:
            return {
                "success": False,
                "error": "The uploaded PDF is empty.",
            }

        text, extraction_method = extract_text_from_pdf(pdf_bytes)
        text = clean_text(text)

        if not text:
            return {
                "success": False,
                "error": (
                    "No readable text was found. Check the PDF "
                    "and verify that Tesseract OCR is installed."
                ),
            }

        warnings = []
        fields = extract_invoice_fields(text)

        # A PDF can have a selectable header and scanned totals or item tables.
        # Retry OCR when the text layer did not provide the rest of the invoice.
        missing_after_text = (
            fields["invoice_date"] is None
            or fields["subtotal"] is None
            or fields["total"] is None
            or not fields["items"]
        )
        if missing_after_text and extraction_method == "PyMuPDF":
            try:
                ocr_text = clean_text(extract_ocr_text_from_pdf(pdf_bytes))
            except pytesseract.TesseractNotFoundError:
                warnings.append(
                    "OCR fallback was unavailable because Tesseract was not "
                    "found. Configure TESSERACT_PATH to read scanned content."
                )
            else:
                if ocr_text:
                    ocr_fields = extract_invoice_fields(ocr_text)
                    added_fields = False

                    for field_name, value in ocr_fields.items():
                        if fields.get(field_name) in (None, []) and value not in (
                            None,
                            [],
                        ):
                            fields[field_name] = value
                            added_fields = True

                    if added_fields:
                        extraction_method = "PyMuPDF + Tesseract OCR"
                        text = f"{text}\n{ocr_text}".strip()
                    else:
                        warnings.append(
                            "OCR fallback ran but did not find additional "
                            "invoice fields."
                        )

        required_fields = [
            "invoice_number",
            "vendor_name",
            "po_number",
            "invoice_date",
            "total",
        ]

        for field in required_fields:
            if fields.get(field) is None:
                warnings.append(
                    f"Missing or unrecognized field: {field}"
                )

        if not fields["items"]:
            warnings.append(
                "No line items were extracted confidently; "
                "manual verification is recommended."
            )

        if fields["invoice_date"]:
            try:
                datetime.strptime(
                    fields["invoice_date"],
                    "%Y-%m-%d"
                )
            except ValueError:
                warnings.append(
                    "Invoice date could not be normalized; "
                    "verify the date manually."
                )

        found_count = sum(
            1 for field in required_fields
            if fields.get(field) is not None
        )

        completeness_score = found_count / len(required_fields)

        return {
            "success": True,
            "fields": fields,
            "extraction_method": extraction_method,
            "completeness_score": completeness_score,
            "warnings": warnings,
            "raw_text": text,
        }

    except pytesseract.TesseractNotFoundError:
        return {
            "success": False,
            "error": (
                "Tesseract OCR was not found. Verify the "
                "TESSERACT_PATH setting in invoice_extractor.py."
            ),
        }

    except Exception as exc:
        return {
            "success": False,
            "error": f"Invoice extraction failed: {exc}",
        }
