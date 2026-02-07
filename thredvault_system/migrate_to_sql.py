# thredvault_system/migrate_to_sql.py
import sqlite3
import csv
import os

DB_FILE = 'thredvault.db'

# Files that have standard headers (Row 1 = Column Names)
STANDARD_FILES = {
    'inventory': 'inventory.csv',
    'sales': 'sales.csv',
    'orders': 'orders.csv'
}

# Financials is special (Key, Value pair)
FINANCIALS_FILE = 'financials.csv'

def init_db():
    if os.path.exists(DB_FILE):
        try:
            os.remove(DB_FILE)
            print("Removed old DB to ensure clean migration.")
        except PermissionError:
            print("Could not delete old DB. It might be in use. Overwriting tables instead.")

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # 1. Create Tables
    print("Creating tables...")
    
    c.execute('''CREATE TABLE IF NOT EXISTS inventory (
        Brand TEXT, Type TEXT, Color TEXT, Size TEXT, 
        Quantity TEXT, WAC_Cost TEXT, WAC_Group TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS sales (
        ID TEXT, Date TEXT, Brand TEXT, Type TEXT, Color TEXT, 
        Size TEXT, Sale_Price TEXT, Profit TEXT, WAC_Group TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS orders (
        Order_ID TEXT, Date TEXT, WAC_Group TEXT, Supplier TEXT, 
        Total_Pieces TEXT, Total_Cost TEXT, Unit_Cost TEXT, 
        Amount_Paid TEXT, Payment_Status TEXT, Status TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS financials (
        key_name TEXT PRIMARY KEY,
        value TEXT
    )''')

    # 2. Import Standard CSV Data (Inventory, Sales, Orders)
    for table, filename in STANDARD_FILES.items():
        if os.path.exists(filename):
            print(f"Migrating {filename} -> Table: {table}...")
            try:
                with open(filename, 'r') as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)
                    if not rows: 
                        print(f"  - {filename} is empty. Skipping.")
                        continue
                    
                    # Dynamic insert based on columns found in CSV
                    cols = rows[0].keys()
                    placeholders = ', '.join(['?'] * len(cols))
                    col_names = ', '.join(cols)
                    query = f"INSERT INTO {table} ({col_names}) VALUES ({placeholders})"
                    
                    for row in rows:
                        c.execute(query, list(row.values()))
            except Exception as e:
                print(f"  - Error reading {filename}: {e}")
        else:
            print(f"Skipping {filename} (Not found)")

    # 3. Import Financials (Special Handling)
    if os.path.exists(FINANCIALS_FILE):
        print("Migrating Financials...")
        try:
            with open(FINANCIALS_FILE, 'r') as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) >= 2:
                        # Ensure we don't insert garbage
                        key = row[0].strip()
                        val = row[1].strip()
                        c.execute("INSERT OR REPLACE INTO financials (key_name, value) VALUES (?, ?)", (key, val))
        except Exception as e:
            print(f"  - Error reading financials: {e}")
    else:
        # Set defaults if file missing
        print("Financials file not found. Setting defaults.")
        c.execute("INSERT OR IGNORE INTO financials (key_name, value) VALUES ('Cash_On_Hand', '0.0')")
        c.execute("INSERT OR IGNORE INTO financials (key_name, value) VALUES ('Outstanding_Payables', '0.0')")

    conn.commit()
    conn.close()
    print("\nSUCCESS! 'thredvault.db' has been created.")

if __name__ == "__main__":
    init_db()