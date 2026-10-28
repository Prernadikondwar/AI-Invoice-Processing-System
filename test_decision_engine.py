
from decision_engine import decide_invoice

validation_report = {
    "status": "Passed",
    "passed_checks": [
        "Invoice number is present.",
        "Invoice date is valid.",
        "Invoice total is numeric and positive.",
    ],
    "failed_checks": [],
    "missing_information": [],
    "warnings": [],
}

match_report = {
    "decision": "Matched - Pending Validation",
    "po_found": True,
    "vendor_verified": True,
    "reasons": [],
}

result = decide_invoice(validation_report, match_report)

print("\n--- DECISION REPORT ---")
print("Decision:", result["decision"])

for reason in result["reasons"]:
    print("-", reason)

print("\n--- DUPLICATE TEST ---")
duplicate_result = decide_invoice(
    validation_report,
    match_report,
    is_duplicate=True,
)
print("Decision:", duplicate_result["decision"])
print("Reason:", duplicate_result["reasons"][0])
