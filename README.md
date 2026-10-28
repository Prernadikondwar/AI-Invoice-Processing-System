# AI Invoice Processing System

A Streamlit prototype for processing vendor invoice PDFs. It extracts invoice
details, checks arithmetic and required fields, compares the invoice with
purchase-order and vendor records, detects duplicate invoices, and displays a
decision with its supporting information.

> **Scope and safety:** This is a demonstration and decision-support project,
> not an accounting system or payment authorization. Decisions are only as
> reliable as the PDF extraction and configured sample data. A person should
> review the source invoice and all results before acting.

## Business problem

Invoice review can require repeatedly reading PDF fields, checking totals,
confirming the vendor and PO, and looking for duplicate submissions. This
prototype brings those checks together in one workflow so reviewers can see
extracted values, validation results, PO comparisons, duplicate status, and a
record of prior runs.

The goal is to make common discrepancies easier to spot and to explain why an
invoice was approved or sent for review. It does not replace an ERP, a human
reviewer, or a full accounts-payable control environment.

## Workflow

1. A reviewer uploads a PDF in the **Process Invoice** tab.
2. PyMuPDF reads selectable text. Tesseract OCR is used for scanned pages and
   as a fallback when a PDF has some selectable text but required fields are
   still missing.
3. The extractor reads the invoice number, vendor, PO number, invoice date,
   subtotal, tax, total, and supported line items. The UI shows the extraction
   method, completeness, and warnings.
4. The validator checks required fields, date format, total amount, line-item
   calculations, subtotal, and tax reconciliation.
5. The matcher checks the PO, associated vendor, approval status, currency,
   PO status, remaining balance, and configured tolerance.
6. The audit logger checks whether the vendor and invoice-number pair was
   previously processed.
7. The decision engine returns **Approved**, **Rejected**, or **Needs Review**.
   The app shows the reasoning and records the run in `data/audit.db`.
8. The **Overview** and **History** tabs show recent processing activity; the
   history can be downloaded as CSV.

## Decision outcomes

- **Approved** when validation explicitly passes, the PO and vendor are
  confirmed, the PO matcher reports a successful match, and there is no
  duplicate or prohibited-transaction hard stop.
- **Rejected** for a confirmed duplicate or a prohibited transaction. The
  prohibited-transaction flag is supported by the decision engine but is not
  currently collected from the UI.
- **Needs Review** when validation does not pass, required information is
  missing, a PO/vendor match cannot be confirmed, or the PO comparison has a
  blocking mismatch.

The decision is deliberately conservative: a missing or uncertain match does
not count as approval.

## Validation and matching rules

### Invoice validation

- Invoice number and vendor name must be present.
- Invoice date must match one of the formats supported by the validator.
- Total must be numeric and greater than zero.
- For each extracted line item, quantity must be greater than zero and unit
  price cannot be negative. When a line amount is present, quantity multiplied
  by unit price must match it within `0.01`.
- When line items and a subtotal are available, their calculated sum must
  match the subtotal within `0.01`.
- When subtotal, tax, and total are available, `subtotal + tax` must match the
  total within `0.02`.
- Missing information and unavailable calculations are reported as warnings
  or review conditions rather than being silently treated as valid.

### Purchase-order and vendor matching

- The invoice PO number must resolve to exactly one PO record.
- The PO must resolve to exactly one vendor, and the invoice vendor name must
  match the vendor record.
- The vendor must be marked `APPROVED`.
- Invoice, PO, and vendor currencies must agree.
- The PO must be `OPEN` or `PARTIALLY_INVOICED`.
- The invoice total must not exceed the remaining PO balance plus the
  configured tolerance.
- Duplicate detection uses the vendor name and invoice number recorded in the
  local audit database.

## Limitations and assumptions

- Invoice extraction uses regular expressions and supports common text-based
  labels and simple line-item rows. Unusual templates, multi-column tables,
  low-quality scans, handwriting, or ambiguous layouts may produce missing or
  incorrect fields. Always compare extracted data with the PDF.
- Scanned-PDF extraction requires the Tesseract OCR executable. If it is not
  installed or configured, selectable PDF text can still be extracted, but
  scanned-only fields cannot be read.
- The supplied PO CSV has PO-level data, not detailed PO line items. The app
  therefore warns that it cannot perform a line-by-line comparison against
  the PO.
- Tax reconciliation assumes the basic equation `subtotal + tax = total`.
  Discounts, shipping, fees, withholding, multiple tax treatments, and other
  adjustments are not modeled.
- Vendor names are compared by normalized exact text, not fuzzy matching.
- Duplicate checks depend on this local SQLite database. They do not detect
  duplicates in other installations, other databases, or invoices processed
  before the local history was created.
- The sample CSVs and demo PDFs are fixtures for local evaluation, not
  production records. Replace them only with data you are authorized to use.
- There is no authentication, role-based access, cloud deployment
  configuration, or production-grade data retention policy in this prototype.

## Requirements

- Python 3.10 or later
- Tesseract OCR for scanned PDFs

The extractor looks for Tesseract at
`C:\Program Files\Tesseract-OCR\tesseract.exe` by default. If it is installed
elsewhere, update `TESSERACT_PATH` in `invoice_extractor.py`.

## Setup

Open PowerShell in the project root and create a virtual environment:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install streamlit pandas pymupdf pytesseract pillow
```

Tesseract is a separate system application; installing the Python
`pytesseract` package does not install the Tesseract executable. Install
Tesseract for your operating system and configure `TESSERACT_PATH` if needed.

If PowerShell prevents environment activation, call the virtual environment's
Python executable directly as shown below.

## Run the application

Run from the project root because the app reads CSV and database files through
relative paths:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Open the local URL printed by Streamlit (usually
`http://localhost:8501`), select **Process Invoice**, upload a PDF, and choose
**Process Invoice**. Review the extracted values, warnings, validation report,
PO comparison, and final decision.

## Tests

Run the focused automated regression tests from the project root:

```powershell
.\.venv\Scripts\python.exe -m unittest test_invoice_extraction_fields test_approval_flow -v
```

These tests cover:

- Extracting inline amounts and amounts printed on the next line.
- Combining selectable PDF text with OCR results when key fields are missing.
- Preserving readable digital fields and reporting a warning if Tesseract is
  unavailable for fallback OCR.
- Validating the extractor's line-item schema and subtotal calculation.
- Approving a valid invoice matched to the sample PO when no duplicate exists.
- Keeping a PO total mismatch from being approved.

Other `test_*.py` files in this repository are runnable examples for their
individual modules; they are not all structured as automated `unittest` cases.

## Project structure

```text
app.py                           Streamlit interface and workflow
invoice_extractor.py             PDF text extraction, OCR, and field parsing
data_validator.py                Required-field and arithmetic validation
po_matcher.py                    PO and vendor comparisons
decision_engine.py               Final approval/rejection/review decision
audit_logger.py                  Duplicate checks and SQLite audit history
data/purchase_orders.csv          Sample purchase-order records
data/vendors (1).csv              Sample vendor records
data/audit.db                     Local processing history (created/updated)
test_invoice_extraction_fields.py Extraction regression tests
test_approval_flow.py             Decision-flow regression tests
```

The app expects the PO and vendor CSV files at the paths shown above. Keep
their required columns intact when replacing the sample CSVs.

## Preparing the project for GitHub

Before pushing:

- Review the CSV files and remove or replace real vendor, contact, purchase
  order, or financial information.
- Do not commit credentials, secrets, real invoices, or data you are not
  authorized to publish.
- Review `data/audit.db`; it contains local processing history and should not
  be pushed if it includes non-public records.
- Generated demo PDFs are synthetic workflow fixtures. Keep their sample
  labeling intact; they are not real invoices and must not be used for payment
  or tax claims.
