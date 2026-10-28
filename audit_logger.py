
import sqlite3
import json
import uuid
from pathlib import Path
from datetime import datetime, timezone

DB_PATH = Path("data/audit.db")


def get_connection():
    """Create the database and its table if needed."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    conn.execute("""
        CREATE TABLE IF NOT EXISTS invoice_runs (
            run_id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            file_name TEXT,
            vendor_name TEXT,
            invoice_number TEXT,
            po_number TEXT,
            invoice_total REAL,
            decision TEXT NOT NULL,
            reasons TEXT,
            extracted_fields TEXT
        )
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_invoice_identity
        ON invoice_runs(vendor_name, invoice_number)
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_po_number
        ON invoice_runs(po_number)
    """)

    conn.commit()
    return conn


def normalize(value):
    """Normalize identity fields for duplicate checks."""
    if value is None:
        return ""
    return " ".join(str(value).casefold().split())


def check_duplicate(vendor_name, invoice_number):
    """Check whether this vendor and invoice number were recorded before."""
    vendor = normalize(vendor_name)
    number = normalize(invoice_number)

    if not vendor or not number:
        return False

    conn = get_connection()
    try:
        row = conn.execute("""
            SELECT 1
            FROM invoice_runs
            WHERE lower(trim(vendor_name)) = ?
              AND lower(trim(invoice_number)) = ?
            LIMIT 1
        """, (vendor, number)).fetchone()

        return row is not None
    finally:
        conn.close()


def record_run(
    file_name,
    invoice,
    decision,
    reasons,
):
    """Save a processing run and its result."""
    run_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()

    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO invoice_runs (
                run_id, timestamp, file_name, vendor_name,
                invoice_number, po_number, invoice_total,
                decision, reasons, extracted_fields
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            run_id,
            timestamp,
            file_name,
            invoice.get("vendor_name"),
            invoice.get("invoice_number"),
            invoice.get("po_number"),
            invoice.get("total"),
            decision,
            json.dumps(reasons, ensure_ascii=False, default=str),
            json.dumps(invoice, ensure_ascii=False, default=str),
        ))
        conn.commit()
    finally:
        conn.close()

    return run_id


def get_approved_invoiced_total(po_number):
    """Return the total recorded as Approved against a PO."""
    conn = get_connection()
    try:
        row = conn.execute("""
            SELECT COALESCE(SUM(invoice_total), 0) AS total
            FROM invoice_runs
            WHERE lower(trim(po_number)) = lower(trim(?))
              AND decision = 'Approved'
        """, (po_number,)).fetchone()

        return float(row["total"])
    finally:
        conn.close()


def get_history(limit=100):
    """Return recent invoice processing runs."""
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT run_id, timestamp, file_name, vendor_name,
                   invoice_number, po_number, invoice_total,
                   decision, reasons
            FROM invoice_runs
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,)).fetchall()

        return [dict(row) for row in rows]
    finally:
        conn.close()
