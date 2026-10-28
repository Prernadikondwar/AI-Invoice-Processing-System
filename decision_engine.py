
def decide_invoice(
    validation_report,
    match_report,
    is_duplicate=False,
    prohibited_transaction=False,
):
    """Return a conservative invoice decision and its reasons."""

    # Confirmed hard-stop conditions
    if is_duplicate:
        return {
            "decision": "Rejected",
            "reasons": ["Confirmed duplicate invoice."],
        }

    if prohibited_transaction:
        return {
            "decision": "Rejected",
            "reasons": ["Transaction is prohibited by policy."],
        }

    if not isinstance(validation_report, dict):
        return {
            "decision": "Needs Review",
            "reasons": ["Invoice validation report is unavailable."],
        }

    if not isinstance(match_report, dict):
        return {
            "decision": "Needs Review",
            "reasons": ["PO matching report is unavailable."],
        }

    reasons = []

    # Validation must explicitly pass
    validation_status = str(
        validation_report.get("status", "")
    ).strip().casefold()

    if validation_status != "passed":
        reasons.append(
            f"Validation did not pass. Status: "
            f"{validation_report.get('status')!r}."
        )

    for key, label in [
        ("failed_checks", "Validation failed"),
        ("missing_information", "Missing information"),
        ("warnings", "Validation warning"),
    ]:
        for item in validation_report.get(key, []) or []:
            reasons.append(f"{label}: {item}")

    # PO and vendor verification
    if not match_report.get("po_found", False):
        reasons.append("A valid PO was not confirmed.")

    if not match_report.get("vendor_verified", False):
        reasons.append("Vendor could not be verified against the PO.")

    match_status = str(
        match_report.get("decision", "")
    ).strip().casefold()

    # Accept only explicitly successful matcher statuses.
    successful_match_statuses = {
        "matched",
        "matched - pending validation",
    }

    if match_status not in successful_match_statuses:
        reasons.append(
            f"PO matching was not successful. "
            f"Status: {match_report.get('decision')!r}."
        )

    for item in match_report.get("reasons", []) or []:
        reasons.append(f"PO matching: {item}")

    # Remove duplicate messages while preserving their order.
    reasons = list(dict.fromkeys(reasons))

    if reasons:
        return {
            "decision": "Needs Review",
            "reasons": reasons,
        }

    return {
        "decision": "Approved",
        "reasons": [
            "Validation passed, PO and vendor were verified, "
            "and no duplicate or prohibited transaction was identified."
        ],
    }
