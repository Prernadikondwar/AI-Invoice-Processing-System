
from pprint import pprint
from pathlib import Path
from invoice_extractor import extract_invoice

pdf_path = input("Enter the full path of your invoice PDF: ").strip().strip('"')

if not Path(pdf_path).is_file():
    print("Error: File not found. Please check the path.")
else:
    result = extract_invoice(pdf_path)
    pprint(result)
