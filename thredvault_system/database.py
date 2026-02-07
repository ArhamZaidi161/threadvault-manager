import csv
import os
import shutil
import sqlite3
from datetime import datetime
import models as md

# --- SQL DATABASE CONNECTION (The Missing Piece) ---
def get_db_connection():
    """Establishes connection to the SQLite database."""
    conn = sqlite3.connect('thredvault.db')
    conn.row_factory = sqlite3.Row
    return conn

# --- CSV HANDLERS (Used by App) ---
def load_csv(filename):
    """Reads a CSV file and returns a list of dictionaries."""
    if not os.path.exists(filename): return []
    with open(filename, mode='r', encoding='utf-8-sig') as file:
        return list(csv.DictReader(file))

def save_csv(filename, columns, data):
    """Writes a list of dictionaries to a CSV file."""
    with open(filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(data)

# --- ID GENERATORS ---
def get_next_order_id():
    orders = load_csv(md.ORDERS_FILE)
    if not orders: return "1"
    max_id = 0
    for row in orders:
        try:
            cid = int(row['Order_ID'])
            if cid > max_id: max_id = cid
        except: continue
    return str(max_id + 1)

def get_next_sale_id():
    sales = load_csv(md.SALES_FILE)
    if not sales: return "1"
    max_id = 0
    for row in sales:
        try:
            cid = int(row.get('ID', 0))
            if cid > max_id: max_id = cid
        except: continue
    return str(max_id + 1)

# --- FINANCIALS ---
def load_financials():
    defaults = {"Cash_On_Hand": 0.0, "Outstanding_Payables": 0.0}
    if not os.path.exists(md.FINANCIALS_FILE): return defaults
    try:
        with open(md.FINANCIALS_FILE, 'r') as f:
            reader = csv.reader(f)
            data = {row[0]: float(row[1]) for row in reader}
        return data
    except: return defaults

def save_financials(cash, payables):
    with open(md.FINANCIALS_FILE, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Cash_On_Hand", cash])
        writer.writerow(["Outstanding_Payables", payables])

def update_cash_on_hand(amount_change):
    fin = load_financials()
    new_cash = fin['Cash_On_Hand'] + amount_change
    save_financials(new_cash, fin['Outstanding_Payables'])
    return new_cash

# --- WAC CALCULATIONS ---
def recalculate_global_wac(target_group):
    """Recalculates WAC for a group based on current inventory."""
    if target_group == "UNKNOWN": return
    
    inventory = load_csv(md.INVENTORY_FILE)
    total_qty = 0
    total_value = 0.0
    
    # 1. Calculate Totals
    for row in inventory:
        # Check explicit group or find it
        row_group = row.get('WAC_Group')
        if not row_group: 
            row_group = md.find_wac_group(row['Brand'], row['Type'])
            
        if row_group == target_group:
            q = int(row['Quantity'])
            c = float(row['WAC_Cost'])
            total_qty += q
            total_value += (q * c)
    
    if total_qty == 0: return

    # 2. Update All Items in Group
    new_wac = round(total_value / total_qty, 2)
    
    for row in inventory:
        row_group = row.get('WAC_Group')
        if not row_group: 
            row_group = md.find_wac_group(row['Brand'], row['Type'])
            
        if row_group == target_group:
            row['WAC_Cost'] = str(new_wac)
            row['WAC_Group'] = target_group
            
    save_csv(md.INVENTORY_FILE, md.INVENTORY_COLUMNS, inventory)