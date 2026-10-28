
import pandas as pd

csv_path = input("Enter the full path of your CSV file: ").strip().strip('"')

try:
    df = pd.read_csv(csv_path)

    print("\nCSV loaded successfully!")
    print("\nColumn names:")
    print(df.columns.tolist())

    print("\nFirst 5 rows:")
    print(df.head())

except FileNotFoundError:
    print("Error: CSV file not found. Check the path.")
except Exception as e:
    print(f"Error reading CSV: {e}")
