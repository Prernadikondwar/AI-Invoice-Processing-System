
from data_validator import validate_invoice

sample_invoice = {
    "invoice_number": "TN-INV-001",
    "invoice_date": "20-10-2026",
    "vendor_name": "TechNova Hardware LLP",
    "subtotal": 200000,
    "tax": 36000,
    "total": 236000,
    "line_items": [
        {
            "description": "Laptops",
            "quantity": 5,
            "unit_price": 40000,
            "amount": 200000,
        }
    ],
}

report = validate_invoice(sample_invoice)

print("\n--- VALIDATION REPORT ---")
print("Status:", report["status"])

for section in [
    "passed_checks",
    "failed_checks",
    "missing_information",
    "warnings",
]:
    print(f"\n{section.replace('_', ' ').title()}:")
    for message in report[section]:
        print("-", message)
