
from datetime import datetime


def validate_invoice(invoice):
    """
    Validate extracted invoice fields and calculations.

    Expected input: dictionary containing extracted invoice fields.
    Returns: passed checks, failed checks, missing information,
             and an overall validation status.
    """

    passed = []
    failed = []
    missing = []
    warnings = []

    # 1. Invoice number
    invoice_number = invoice.get("invoice_number")

    if invoice_number is None or not str(invoice_number).strip():
        missing.append("Invoice number is missing.")
    else:
        passed.append("Invoice number is present.")

    # 2. Invoice date
    invoice_date = invoice.get("invoice_date")

    if not invoice_date:
        missing.append("Invoice date is missing.")
    else:
        date_formats = [
            "%Y-%m-%d",
            "%d-%m-%Y",
            "%d/%m/%Y",
            "%d-%b-%Y",
            "%d %b %Y",
            "%d %B %Y",
            "%d/%m/%y",
        ]

        valid_date = False

        for date_format in date_formats:
            try:
                datetime.strptime(str(invoice_date).strip(), date_format)
                valid_date = True
                break
            except ValueError:
                continue

        if valid_date:
            passed.append("Invoice date is valid.")
        else:
            failed.append(
                f"Invoice date has an unsupported or invalid format: {invoice_date}"
            )

    # 3. Vendor
    vendor_name = invoice.get("vendor_name")

    if not vendor_name or not str(vendor_name).strip():
        missing.append("Vendor name is missing.")
    else:
        passed.append("Vendor name is present.")

    # 4. Total amount
    total = invoice.get("total")

    try:
        if total is None or str(total).strip() == "":
            missing.append("Invoice total is missing.")
        else:
            total_value = float(
                str(total).replace(",", "").replace("₹", "").strip()
            )

            if total_value <= 0:
                failed.append("Invoice total must be greater than zero.")
            else:
                passed.append("Invoice total is numeric and positive.")

    except (ValueError, TypeError):
        failed.append("Invoice total is not numeric.")

    # 5. Line items and their calculations
    line_items = invoice.get("line_items")
    if line_items is None:
        line_items = invoice.get("items") or []
    calculated_subtotal = 0.0
    line_items_valid = True

    if not line_items:
        warnings.append(
            "No line items were extracted; quantity and price checks could not run."
        )
    else:
        for index, item in enumerate(line_items, start=1):
            try:
                quantity = float(item.get("quantity"))
                unit_price = float(
                    str(item.get("unit_price")).replace(",", "").replace("₹", "")
                )

                if quantity <= 0 or unit_price < 0:
                    raise ValueError

                line_total = quantity * unit_price
                calculated_subtotal += line_total

                extracted_line_total = item.get(
                    "amount",
                    item.get("line_total"),
                )

                if extracted_line_total not in (None, ""):
                    extracted_line_total = float(
                        str(extracted_line_total)
                        .replace(",", "")
                        .replace("₹", "")
                    )

                    if abs(line_total - extracted_line_total) > 0.01:
                        failed.append(
                            f"Line item {index}: quantity × unit price "
                            f"does not match the stated line amount."
                        )
                        line_items_valid = False

            except (ValueError, TypeError, AttributeError):
                failed.append(
                    f"Line item {index}: quantity or unit price is missing "
                    f"or invalid."
                )
                line_items_valid = False

        if line_items_valid:
            passed.append("Line-item quantities and prices are valid.")

        # Compare calculated subtotal if an extracted subtotal exists.
        subtotal = invoice.get("subtotal")

        if subtotal not in (None, ""):
            try:
                subtotal_value = float(
                    str(subtotal).replace(",", "").replace("₹", "")
                )

                if abs(calculated_subtotal - subtotal_value) > 0.01:
                    failed.append(
                        f"Calculated subtotal ₹{calculated_subtotal:.2f} "
                        f"does not match extracted subtotal ₹{subtotal_value:.2f}."
                    )
                else:
                    passed.append("Calculated subtotal matches the invoice.")
            except (ValueError, TypeError):
                failed.append("Extracted subtotal is not numeric.")

    # 6. Tax reconciliation
    tax = invoice.get("tax")
    subtotal = invoice.get("subtotal")

    if tax not in (None, "") and subtotal not in (None, "") and total not in (None, ""):
        try:
            tax_value = float(
                str(tax).replace(",", "").replace("₹", "")
            )
            subtotal_value = float(
                str(subtotal).replace(",", "").replace("₹", "")
            )
            total_value = float(
                str(total).replace(",", "").replace("₹", "")
            )

            # Basic reconciliation: subtotal + tax = total.
            # Additional charges or discounts must be handled separately.
            if abs((subtotal_value + tax_value) - total_value) > 0.02:
                failed.append(
                    "Subtotal + tax does not match the invoice total."
                )
            else:
                passed.append("Subtotal and tax reconcile with the total.")
        except (ValueError, TypeError):
            failed.append("Subtotal, tax, or total could not be reconciled.")
    else:
        warnings.append(
            "Tax reconciliation could not run because subtotal, tax, "
            "or total is missing."
        )

    # 7. Overall status
    if failed:
        status = "Failed"
    elif missing or warnings:
        status = "Needs Review"
    else:
        status = "Passed"

    return {
        "status": status,
        "passed_checks": passed,
        "failed_checks": failed,
        "missing_information": missing,
        "warnings": warnings,
    }
