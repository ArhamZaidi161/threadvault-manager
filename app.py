import csv
import os
import shutil
from datetime import datetime, date

# --- CONFIGURATION ---
INVENTORY_FILE = 'inventory.csv'
SALES_FILE = 'sales.csv'
ORDERS_FILE = 'orders.csv'
FINANCIALS_FILE = 'financials.csv'
BACKUP_DIR = 'backups'

# Columns
ORDER_COLUMNS = ["Order_ID", "Date", "WAC_Group", "Supplier", "Total_Pieces", 
                 "Total_Cost", "Unit_Cost", "Amount_Paid", "Payment_Status", "Status"]

INVENTORY_COLUMNS = ["Brand", "Type", "Color", "Size", "Quantity", "WAC_Cost", "WAC_Group"]
SALES_COLUMNS = ["ID", "Date", "Brand", "Type", "Color", "Size", "Sale_Price", "Profit", "WAC_Group"]

# --- DATA MAPPING ---
VALID_WAC_GROUPS = [
    "Ess_HoodiePant", "Ess_TeeShort", "Spdr_HoodiePant", "Den_HoodiePant", "Eric_EmanShorts", "YZY_Slides"
]

WAC_TO_BRAND = {
    "Ess_HoodiePant": "ESSENTIALS", "Ess_TeeShort": "ESSENTIALS",
    "Spdr_HoodiePant": "SP5DER", "Den_HoodiePant": "DENIM TEARS",
    "Eric_EmanShorts": "ERIC EMANUEL", "YZY_Slides": "YZY"
}

WAC_TO_TYPES = {
    "Ess_HoodiePant": ["HOODIE", "PANT"], "Ess_TeeShort": ["TEE", "SHORTS"],
    "Spdr_HoodiePant": ["HOODIE", "PANT"], "Den_HoodiePant": ["HOODIE", "PANT"],
    "Eric_EmanShorts": ["SHORTS"], "YZY_Slides": ["SLIDES"]
}

SIZE_SORT_ORDER = {
    "XXS": 0, "XS": 1, "S": 2, "M": 3, "L": 4, "XL": 5, "XXL": 6, "ONE SIZE": 99,
    "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9, "10": 10, "11": 11, "12": 12
}

SIZE_MAP = {
    "ESSENTIALS": ["XS", "S", "M", "L"],
    "SP5DER": ["S", "M", "L"],
    "DENIM TEARS": ["S", "M", "L"],
    "ERIC EMANUEL": ["XS", "S", "M", "L", "XL"],
    "YZY": ["4", "5", "6", "7", "8", "9", "10", "11", "12"]
}

# --- PRIORITY LISTS FOR SORTING ---
BRAND_PRIORITY = ["ESSENTIALS", "DENIM TEARS", "SP5DER", "ERIC EMANUEL", "YZY"]

COLOR_PRIORITY = {
    "ESSENTIALS": ["B22", "L/O", "D/O", "1977 IRON", "1977 D/O", "BLACK"],
    "SP5DER": ["PINK", "BLUE", "BLACK"],
    "DENIM TEARS": ["BLACK", "GREY"],
    "ERIC EMANUEL": ["BLACK", "NAVY", "GREY", "LIGHT BLUE", "RED", "WHITE"],
    "YZY": ["ONYX", "BONE"]
}

BRAND_COLORS = COLOR_PRIORITY 

BRAND_TYPES = {
    "ESSENTIALS": ["HOODIE", "PANT", "TEE", "SHORTS"],
    "SP5DER": ["HOODIE", "PANT"],
    "DENIM TEARS": ["HOODIE", "PANT"],
    "ERIC EMANUEL": ["SHORTS"],
    "YZY": ["SLIDES"]
}

# --- HELPER FUNCTIONS ---

def create_backup():
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    files = [INVENTORY_FILE, SALES_FILE, ORDERS_FILE, FINANCIALS_FILE]
    for f in files:
        if os.path.exists(f):
            shutil.copy2(f, os.path.join(BACKUP_DIR, f"{f}_{timestamp}.bak"))

def safe_float(value):
    if not value or value.strip() == "": return 0.0
    try: return float(value)
    except ValueError: return 0.0

def clean_text(text):
    """Normalize text to uppercase and stripped to prevent duplicates."""
    if not text: return ""
    return text.strip().upper()

def get_valid_float(prompt, allow_empty_as_zero=False):
    while True:
        entry = input(prompt).strip()
        if entry.upper() == 'CANCEL': return None
        if allow_empty_as_zero and entry == "": return 0.0
        try:
            value = float(entry)
            if value < 0:
                print("Value cannot be negative.")
                continue
            return value
        except ValueError:
            print("Invalid number. Type a number or 'CANCEL'.")

def get_selection(prompt, options, custom_label=None):
    print(f"\n{prompt}")
    for i, opt in enumerate(options):
        print(f"{i + 1}. {opt}")
    if custom_label:
        print(f"{len(options) + 1}. [{custom_label}]")
    print("0. BACK")

    while True:
        choice = input("Select option #: ").strip().upper()
        if choice == '0' or choice == 'BACK' or choice == '': return None
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(options): return options[idx]
            elif custom_label and idx == len(options):
                val = input(f"Enter {custom_label}: ").strip().upper()
                return clean_text(val) if val else None 
        if choice in options: return choice
        if custom_label and not choice.isdigit(): return clean_text(choice)
        print("Invalid selection.")

def confirm_action(summary_text):
    print("\n" + "="*40)
    print("REVIEW DETAILS")
    print("="*40)
    print(summary_text)
    print("="*40)
    while True:
        ans = input("Is this correct? (y = save / n = retry / c = cancel menu): ").strip().lower()
        if ans == 'y': return "SAVE"
        if ans == 'n': return "RETRY"
        if ans == 'c': return "CANCEL"

def load_csv(filename):
    if not os.path.exists(filename): return []
    with open(filename, mode='r') as file:
        return list(csv.DictReader(file))

def save_csv(filename, columns, data):
    with open(filename, mode='w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(data)

def get_next_order_id():
    orders = load_csv(ORDERS_FILE)
    if not orders: return "1"
    max_id = 0
    latest_order = None
    for row in orders:
        try:
            cid = int(row['Order_ID'])
            if cid > max_id: 
                max_id = cid
                latest_order = row
        except: continue
    # Reuse ID if the latest one was Cancelled (not permanent delete, but status cancelled)
    if latest_order and latest_order.get('Status') == 'Cancelled':
        return str(max_id)
    return str(max_id + 1)

def get_next_sale_id():
    sales = load_csv(SALES_FILE)
    if not sales: return "1"
    max_id = 0
    for row in sales:
        try:
            cid = int(row.get('ID', 0))
            if cid > max_id: max_id = cid
        except: continue
    return str(max_id + 1)

def find_wac_group(brand, type_):
    for group, types in WAC_TO_TYPES.items():
        mapped_brand = WAC_TO_BRAND.get(group)
        if mapped_brand == brand and type_ in types:
            return group
    return "UNKNOWN"

def get_current_global_wac(target_group):
    if target_group == "UNKNOWN": return 0.0
    inventory = load_csv(INVENTORY_FILE)
    total_qty = 0
    total_value = 0.0
    for row in inventory:
        row_group = row.get('WAC_Group')
        if not row_group: row_group = find_wac_group(row['Brand'], row['Type'])
        if row_group == target_group:
            q = int(row['Quantity'])
            c = safe_float(row['WAC_Cost'])
            total_qty += q
            total_value += (q * c)
    if total_qty == 0: return 0.0
    return total_value / total_qty

def recalculate_global_wac(target_group):
    if target_group == "UNKNOWN": return
    inventory = load_csv(INVENTORY_FILE)
    total_qty = 0
    total_value = 0.0
    for row in inventory:
        row_group = row.get('WAC_Group')
        if not row_group: row_group = find_wac_group(row['Brand'], row['Type'])
        if row_group == target_group:
            q = int(row['Quantity'])
            c = safe_float(row['WAC_Cost'])
            total_qty += q
            total_value += (q * c)
    
    if total_qty == 0: return
    new_wac_str = str(round(total_value / total_qty, 2))
    
    for row in inventory:
        row_group = row.get('WAC_Group')
        if not row_group: row_group = find_wac_group(row['Brand'], row['Type'])
        if row_group == target_group:
            row['WAC_Cost'] = new_wac_str
            row['WAC_Group'] = target_group
            
    save_csv(INVENTORY_FILE, INVENTORY_COLUMNS, inventory)

def load_financials():
    defaults = {"Cash_On_Hand": 0.0, "Outstanding_Payables": 0.0}
    if not os.path.exists(FINANCIALS_FILE): return defaults
    try:
        with open(FINANCIALS_FILE, 'r') as f:
            reader = csv.reader(f)
            data = {row[0]: safe_float(row[1]) for row in reader}
        return data
    except: return defaults

def save_financials(cash, payables):
    with open(FINANCIALS_FILE, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Cash_On_Hand", cash])
        writer.writerow(["Outstanding_Payables", payables])

def update_cash_on_hand(amount_change):
    """
    Updates cash on hand. 
    Positive amount = Add Cash (Sale). 
    Negative amount = Spend Cash (Purchase/Refund).
    """
    fin = load_financials()
    current_cash = fin['Cash_On_Hand']
    new_cash = current_cash + amount_change
    save_financials(new_cash, fin['Outstanding_Payables'])
    return new_cash

def print_aligned(label, value):
    print(f"{label:<20} {value}")

def print_header(text):
    print("\n" + "="*85)
    print(f" {text}")
    print("="*85)

# --- SORT & DISPLAY UTILS ---

def get_color_rank(brand, color):
    try:
        return COLOR_PRIORITY.get(brand, []).index(color)
    except ValueError:
        return 999

def get_group_rank(brand, type_):
    b = brand.upper()
    t = type_.upper()
    
    if b == "ESSENTIALS":
        if t in ["HOODIE", "PANT"]: return 1
        return 2
    if b == "DENIM TEARS": return 3
    if b == "SP5DER": return 4
    if b == "ERIC EMANUEL": return 5
    if b == "YZY": return 6
    return 99

def get_group_name(brand, type_):
    rank = get_group_rank(brand, type_)
    if rank == 1: return "ESSENTIALS (Hoodies/Pants)"
    if rank == 2: return "ESSENTIALS (Tees/Shorts)"
    return brand

# --- FEATURES ---

def create_purchase_order():
    print_header("CREATE PURCHASE ORDER (Multi-Brand)")
    new_order_id = get_next_order_id()
    print(f"Generated Order ID: #{new_order_id}")
    
    supplier = input("Supplier Name: ").strip()
    if not supplier: return
    
    date_str = input(f"Order Date (Enter for Today {date.today().strftime('%m/%d/%Y')}): ").strip()
    if not date_str: date_str = date.today().strftime("%m/%d/%Y")

    cart = [] 

    while True:
        print(f"\n--- Adding Item #{len(cart)+1} to Order #{new_order_id} ---")
        wac_group = get_selection("Select Brand/Category Group:", VALID_WAC_GROUPS, "Add Custom")
        if not wac_group: break 

        pcs = get_valid_float(f"Pieces for {wac_group}: ")
        if pcs is None: continue
        
        line_cost = get_valid_float(f"Total Cost for these {int(pcs)} pcs ($): ")
        if line_cost is None: continue
        
        unit_cost = line_cost / pcs if pcs > 0 else 0
        
        print(f"   -> Added: {wac_group} | {int(pcs)} pcs @ ${unit_cost:.2f}/ea")
        cart.append({
            "WAC_Group": wac_group,
            "Total_Pieces": pcs,
            "Total_Cost": line_cost,
            "Unit_Cost": unit_cost
        })
        
        add_more = input("\nAdd another brand/group to this order? (y/n): ").lower()
        if add_more != 'y': break
    
    if not cart:
        print("Empty order. Cancelled.")
        return

    grand_total_cost = sum(item['Total_Cost'] for item in cart)
    
    print("\n" + "-" * 40)
    print(f"ORDER SUMMARY | Supplier: {supplier}")
    print("-" * 40)
    for i, item in enumerate(cart):
        print(f"{i+1}. {item['WAC_Group']:<20} {int(item['Total_Pieces'])}pcs   ${item['Total_Cost']:,.2f}")
    print("-" * 40)
    print_aligned("TOTAL COST:", f"${grand_total_cost:,.2f}")
    
    print("\nPayment Status:")
    print("1. Paid Full")
    print("2. Unpaid / Net Terms")
    print("3. Partial Deposit")
    pay_choice = input("Select: ").strip()
    
    total_paid = 0.0
    payment_status = "Unpaid"
    
    if pay_choice == '1':
        total_paid = grand_total_cost
        payment_status = "Paid"
    elif pay_choice == '3':
        total_paid = get_valid_float("Total Amount Paid Upfront: $")
        if total_paid is None: return
        payment_status = "Partial"
    
    remaining_balance = grand_total_cost - total_paid
    if remaining_balance > 0:
        print(f"[!] Remaining Balance to Pay: ${remaining_balance:,.2f}")

    if confirm_action(f"Save Order #{new_order_id} with {len(cart)} items?") == "SAVE":
        existing_orders = load_csv(ORDERS_FILE)
        
        for item in cart:
            if grand_total_cost > 0:
                proportion = item['Total_Cost'] / grand_total_cost
                line_paid = total_paid * proportion
            else:
                line_paid = 0

            line_status = payment_status 
            if line_paid >= item['Total_Cost']: line_status = "Paid"
            elif line_paid == 0: line_status = "Unpaid"
            else: line_status = "Partial"

            new_row = {
                "Order_ID": new_order_id, 
                "Date": date_str, 
                "WAC_Group": item['WAC_Group'],
                "Supplier": supplier, 
                "Total_Pieces": str(int(item['Total_Pieces'])),
                "Total_Cost": str(item['Total_Cost']), 
                "Unit_Cost": str(round(item['Unit_Cost'], 2)),
                "Amount_Paid": str(round(line_paid, 2)), 
                "Payment_Status": line_status,
                "Status": "Ordered"
            }
            existing_orders.append(new_row)
        
        save_csv(ORDERS_FILE, ORDER_COLUMNS, existing_orders)
        
        # --- FINANCIAL UPDATE ---
        if total_paid > 0:
            new_cash = update_cash_on_hand(-total_paid) # Subtract spending
            print(f"[FINANCE] Cash updated: -${total_paid:.2f} (Bal: ${new_cash:.2f})")
            
        print(f"Order #{new_order_id} Saved Successfully!")

def receive_stock():
    print_header("RECEIVE STOCK")
    all_orders = load_csv(ORDERS_FILE)
    
    pending_rows = [r for r in all_orders if r['Status'] != 'Received']
    
    if not pending_rows:
        print("No pending orders.")
        return

    print(f"\n{'ID':<5} {'SUPPLIER':<15} {'GROUP':<15} {'PCS':<5} {'STATUS'}")
    print("-" * 50)
    for row in pending_rows:
        print(f"#{row['Order_ID']:<4} {row['Supplier']:<15} {row['WAC_Group']:<15} {row['Total_Pieces']:<5} {row['Status']}")
        
    print("\nNote: You must receive each line individually.")
    order_id = input("Enter Order ID to Receive: ").strip()
    
    order_lines = [r for r in pending_rows if r['Order_ID'] == order_id]
    
    if not order_lines:
        print("Order ID not found or already fully received.")
        return

    target_row = None
    if len(order_lines) > 1:
        print(f"\nOrder #{order_id} has multiple items:")
        for i, r in enumerate(order_lines):
            print(f"{i+1}. {r['WAC_Group']} ({r['Total_Pieces']} pcs)")
        sel = input("Select item to receive #: ")
        if sel.isdigit() and 1 <= int(sel) <= len(order_lines):
            target_row = order_lines[int(sel)-1]
    else:
        target_row = order_lines[0]

    if not target_row: return

    wac_group = target_row['WAC_Group']
    unit_cost = safe_float(target_row['Unit_Cost'])
    
    print(f"\nReceiving: {wac_group}")
    print(f"Cost Basis: ${unit_cost:.2f}/unit")
    
    brand = WAC_TO_BRAND.get(wac_group, "UNKNOWN")
    allowed_types = WAC_TO_TYPES.get(wac_group, [])
    
    if brand == "UNKNOWN":
        brand = input("Enter Brand Name: ").strip().upper()
    
    while True:
        if len(allowed_types) == 1:
            type_ = allowed_types[0]
            print(f"Type: {type_}")
            single_type = True
        elif allowed_types:
            type_ = get_selection(f"Select Type for {brand}:", allowed_types, "Custom")
            single_type = False
        else:
            type_ = input("Enter Type: ").strip().upper()
            single_type = False
            
        if not type_: break

        while True:
            colors = BRAND_COLORS.get(brand, [])
            color = get_selection(f"Color for {type_}:", colors, "Custom")
            if not color: break
            
            valid_sizes = SIZE_MAP.get(brand, ["S", "M", "L"])
            staged = []
            
            print(f"\n--- Batch Entry: {brand} {type_} {color} ---")
            for size in valid_sizes:
                q = get_valid_float(f"  Qty {size}: ", True)
                if q is None: break
                if q > 0: staged.append((size, int(q)))
            
            if staged:
                inventory = load_csv(INVENTORY_FILE)
                for size, qty in staged:
                    found = False
                    for row in inventory:
                        if (row['Brand'] == brand and row['Type'] == type_ and 
                            row['Color'] == color and row['Size'] == size):
                            row['Quantity'] = str(int(row['Quantity']) + qty)
                            row['WAC_Group'] = wac_group
                            found = True
                    if not found:
                        inventory.append({
                            "Brand": brand, "Type": type_, "Color": color, "Size": size,
                            "Quantity": str(qty), "WAC_Cost": str(unit_cost), "WAC_Group": wac_group
                        })
                save_csv(INVENTORY_FILE, INVENTORY_COLUMNS, inventory)
                recalculate_global_wac(wac_group)
                print("  Saved Batch.")
                
            print(f"Finished {color}. Add another Color?")
        
        if single_type: break
        else: print(f"Finished {type_}. Add another Type?")

    close = input(f"Mark {wac_group} (Order #{order_id}) as Received? (y/n): ").lower()
    if close == 'y':
        current_data = load_csv(ORDERS_FILE)
        for r in current_data:
            if r['Order_ID'] == order_id and r['WAC_Group'] == wac_group and r['Status'] != 'Received':
                r['Status'] = "Received"
                break
        save_csv(ORDERS_FILE, ORDER_COLUMNS, current_data)
        print("Item Closed.")

def record_sale():
    print_header("RECORD SALE")
    brands = list(SIZE_MAP.keys())
    brand = get_selection("Brand:", brands, "Custom")
    if not brand: return

    brand_types = BRAND_TYPES.get(brand, [])
    type_ = get_selection("Type:", brand_types, "Custom")
    if not type_: return

    colors = BRAND_COLORS.get(brand, [])
    color = get_selection("Color:", colors, "Custom")
    if not color: return

    sizes = SIZE_MAP.get(brand, ["S", "M", "L"])
    size = get_selection("Size:", sizes, "Custom")
    if not size: return

    inventory = load_csv(INVENTORY_FILE)
    found_item = None
    for row in inventory:
        if (row['Brand'] == brand and row['Color'] == color and 
            row['Size'] == size and row['Type'] == type_):
            found_item = row
            break
    
    if not found_item:
        print("Item not found! Try again.")
        return

    if int(found_item['Quantity']) <= 0:
        print("Stock is 0! Cannot sell.")
        return

    print(f"Found: {brand} {type_} {color} {size} (Stock: {found_item['Quantity']})")
    price = get_valid_float("Sale Price: $")
    if price is None: return

    cost = safe_float(found_item['WAC_Cost'])
    profit = price - cost
    wac_grp = found_item.get('WAC_Group', 'UNKNOWN')

    if confirm_action(f"Sell 1x for ${price:.2f} (Profit: ${profit:.2f})") == "SAVE":
        found_item['Quantity'] = str(int(found_item['Quantity']) - 1)
        save_csv(INVENTORY_FILE, INVENTORY_COLUMNS, inventory)
        
        sales = load_csv(SALES_FILE)
        new_sale_id = get_next_sale_id()
        sales.append({
            "ID": new_sale_id,
            "Date": date.today().strftime("%m/%d/%Y"),
            "Brand": brand, "Type": type_, "Color": color, "Size": size,
            "Sale_Price": str(price), "Profit": str(round(profit, 2)),
            "WAC_Group": wac_grp
        })
        save_csv(SALES_FILE, SALES_COLUMNS, sales)
        
        # --- FINANCIAL UPDATE ---
        new_cash = update_cash_on_hand(price)
        print(f"[FINANCE] Cash added: +${price:.2f} (Bal: ${new_cash:.2f})")
        print("Sale Recorded!")

# --- SALES MANAGEMENT (RETURNS & EDITS) ---
def manage_sales_menu():
    print_header("SALES & RETURNS MANAGEMENT")
    while True:
        print("1. View Recent Sales")
        print("2. Edit Sale Price")
        print("3. PROCESS RETURN (Refund & Restock)")
        print("0. Back")
        opt = input("Select: ").strip()
        
        if opt == '0' or opt == '': return
        elif opt == '1': view_recent_sales()
        elif opt == '2': edit_sale_price()
        elif opt == '3': process_return()

def view_recent_sales():
    sales = load_csv(SALES_FILE)
    if not sales:
        print("No sales records.")
        return
    
    # Show last 10
    print(f"\n{'ID':<4} {'DATE':<10} {'ITEM':<35} {'PRICE':<10}")
    print("-" * 65)
    for row in sales[-10:]:
        desc = f"{row['Brand']} {row['Type']} {row['Color']} {row['Size']}"
        print(f"#{row['ID']:<3} {row['Date']:<10} {desc[:35]:<35} ${safe_float(row['Sale_Price']):.2f}")
    input("\nPress Enter...")

def edit_sale_price():
    sale_id = input("Enter Sale ID to Edit: ").strip()
    sales = load_csv(SALES_FILE)
    
    target_idx = -1
    for i, r in enumerate(sales):
        if r['ID'] == sale_id:
            target_idx = i
            break
    
    if target_idx == -1:
        print("Sale ID not found.")
        return
        
    sale = sales[target_idx]
    old_price = safe_float(sale['Sale_Price'])
    print(f"Current Price: ${old_price:.2f}")
    
    new_price = get_valid_float("Enter New Correct Price: $")
    if new_price is not None:
        # Adjust financials: Remove old amount, add new amount
        diff = new_price - old_price
        update_cash_on_hand(diff)
        
        sale['Sale_Price'] = str(new_price)
        # Recalculate profit using derived cost
        cost = old_price - safe_float(sale['Profit']) 
        sale['Profit'] = str(new_price - cost)
        
        save_csv(SALES_FILE, SALES_COLUMNS, sales)
        print(f"Updated. Cash adjusted by ${diff:.2f}.")

def process_return():
    print("\n--- PROCESS RETURN ---")
    sale_id = input("Enter Sale ID to Return: ").strip()
    sales = load_csv(SALES_FILE)
    
    target_idx = -1
    for i, r in enumerate(sales):
        if r['ID'] == sale_id:
            target_idx = i
            break
    
    if target_idx == -1:
        print("Sale ID not found.")
        return
        
    sale = sales[target_idx]
    refund_amount = safe_float(sale['Sale_Price'])
    
    print(f"Returning: {sale['Brand']} {sale['Type']} {sale['Color']} {sale['Size']}")
    print(f"Refund Amount: ${refund_amount:.2f}")
    
    if confirm_action("Confirm Return & Refund?") == "SAVE":
        # 1. Update Financials (Subtract Refund)
        new_cash = update_cash_on_hand(-refund_amount)
        print(f"[FINANCE] Refunded ${refund_amount:.2f} (Bal: ${new_cash:.2f})")
        
        # 2. Add Stock Back to Inventory
        inventory = load_csv(INVENTORY_FILE)
        found = False
        for row in inventory:
            if (row['Brand'] == sale['Brand'] and row['Type'] == sale['Type'] and 
                row['Color'] == sale['Color'] and row['Size'] == sale['Size']):
                row['Quantity'] = str(int(row['Quantity']) + 1)
                found = True
                break
        
        if not found:
            # Create new row using WAC Group from sale if possible
            cost_basis = refund_amount - safe_float(sale['Profit'])
            inventory.append({
                "Brand": sale['Brand'], "Type": sale['Type'], "Color": sale['Color'],
                "Size": sale['Size'], "Quantity": "1", 
                "WAC_Cost": str(cost_basis), "WAC_Group": sale['WAC_Group']
            })
        
        save_csv(INVENTORY_FILE, INVENTORY_COLUMNS, inventory)
        print("[INVENTORY] Item restocked.")
        
        # 3. Remove Sale Record
        del sales[target_idx]
        save_csv(SALES_FILE, SALES_COLUMNS, sales)
        print("[SALES] Record removed.")

# --- DASHBOARDS ---

def view_dashboard_menu():
    print_header("CEO DASHBOARD")
    while True:
        print("1. Liquidity & Lifetime Totals")
        print("2. Custom Date Range Performance")
        print("0. Back")
        opt = input("Select: ").strip()
        
        if opt == '0' or opt == '': return
        elif opt == '1': dashboard_liquidity()
        elif opt == '2': dashboard_period(auto=False)

def view_monthly_performance():
    print("\n--- CURRENT MONTH PERFORMANCE ---")
    dashboard_period(auto=True)

def dashboard_period(auto=False):
    today = date.today()
    if auto:
        start_str = today.strftime(f"%m/01/%Y")
        end_str = today.strftime("%m/%d/%Y")
    else:
        print("\n--- CUSTOM PERIOD ---")
        start_str = input("Start Date (mm/dd/yyyy) [Enter for 1st of month]: ").strip()
        end_str = input("End Date (mm/dd/yyyy) [Enter for Today]: ").strip()
        if not start_str: start_str = today.strftime(f"%m/01/%Y")
        if not end_str: end_str = today.strftime("%m/%d/%Y")
    
    try:
        start_dt = datetime.strptime(start_str, "%m/%d/%Y").date()
        end_dt = datetime.strptime(end_str, "%m/%d/%Y").date()
    except:
        print("Invalid date format.")
        return

    sales = load_csv(SALES_FILE)
    rev = 0.0
    profit = 0.0
    units = 0
    
    for row in sales:
        try:
            s_date = datetime.strptime(row['Date'], "%m/%d/%Y").date()
            if start_dt <= s_date <= end_dt:
                rev += safe_float(row['Sale_Price'])
                profit += safe_float(row['Profit'])
                units += 1
        except: continue
        
    margin = (profit / rev * 100) if rev > 0 else 0.0
    
    print("-" * 30)
    print_aligned("Period:", f"{start_str} to {end_str}")
    print_aligned("Revenue:", f"${rev:,.2f}")
    print_aligned("Profit:", f"${profit:,.2f}")
    print_aligned("Gross Margin:", f"{margin:.2f}%")
    print_aligned("Units Sold:", f"{units}")
    print("-" * 30)
    input("\nPress Enter...")

def dashboard_liquidity():
    print_header("LIQUIDITY & LIFETIME")
    fin = load_financials()
    
    print_aligned("Cash on Hand:", f"${fin.get('Cash_On_Hand', 0):,.2f}")
    print_aligned("Outstanding:", f"${fin.get('Outstanding_Payables', 0):,.2f}")
    
    update = input("\nUpdate these values? (y/n): ").lower()
    
    if update == 'y':
        val = get_valid_float("New Cash Balance (Enter to skip): $", True)
        if val is not None:
            fin['Cash_On_Hand'] = val
        pay = get_valid_float("New Outstanding Payables (Enter to skip): $", True)
        if pay is not None:
            fin['Outstanding_Payables'] = pay
        save_financials(fin['Cash_On_Hand'], fin['Outstanding_Payables'])

    orders = load_csv(ORDERS_FILE)
    committed_cash = 0.0
    total_bought_qty = 0
    
    for row in orders:
        if row['Status'] != 'Cancelled':
            cost = safe_float(row.get('Total_Cost'))
            paid = safe_float(row.get('Amount_Paid'))
            committed_cash += (cost - paid)
            total_bought_qty += int(row.get('Total_Pieces', 0))

    inventory = load_csv(INVENTORY_FILE)
    on_hand_val = 0.0
    for row in inventory:
        on_hand_val += (int(row['Quantity']) * safe_float(row['WAC_Cost']))

    sales = load_csv(SALES_FILE)
    lifetime_rev = 0.0
    lifetime_profit = 0.0
    lifetime_sold = 0
    for row in sales:
        lifetime_rev += safe_float(row['Sale_Price'])
        lifetime_profit += safe_float(row['Profit'])
        lifetime_sold += 1

    net_worth = fin['Cash_On_Hand'] + on_hand_val - committed_cash
    
    print("\n" + "="*35)
    print("FINANCIAL SNAPSHOT")
    print_aligned("Cash on Hand:", f"${fin['Cash_On_Hand']:,.2f}")
    print_aligned("Outstanding:", f"${committed_cash:,.2f}")
    print_aligned("Available Cash:", f"${(fin['Cash_On_Hand'] - committed_cash):,.2f}")
    print_aligned("Stock Value:", f"${on_hand_val:,.2f}")
    print_aligned("Net Worth:", f"${net_worth:,.2f}")
    
    print("\nLIFETIME TOTALS")
    print_aligned("Total Revenue:", f"${lifetime_rev:,.2f}")
    print_aligned("Total Profit:", f"${lifetime_profit:,.2f}")
    print_aligned("Sold / Bought:", f"{lifetime_sold} / {total_bought_qty}")
    if lifetime_sold > 0:
        print_aligned("Avg Rev/Pc:", f"${lifetime_rev/lifetime_sold:,.2f}")
        print_aligned("Avg Prof/Pc:", f"${lifetime_profit/lifetime_sold:,.2f}")
    print("="*35)
    input("\nPress Enter...")

def view_brand_performance():
    print_header("BRAND PERFORMANCE")
    stats = {}
    
    inv = load_csv(INVENTORY_FILE)
    for row in inv:
        g = row.get('WAC_Group', 'UNKNOWN')
        if g not in stats: stats[g] = {'Stock':0, 'Val':0.0, 'Rev':0.0, 'Prof':0.0}
        q = int(row['Quantity'])
        stats[g]['Stock'] += q
        stats[g]['Val'] += (q * safe_float(row['WAC_Cost']))
        
    sales = load_csv(SALES_FILE)
    for row in sales:
        g = row.get('WAC_Group', 'UNKNOWN')
        if not g or g == 'None':
            g = find_wac_group(row['Brand'], row['Type'])
            
        if g not in stats: stats[g] = {'Stock':0, 'Val':0.0, 'Rev':0.0, 'Prof':0.0}
        stats[g]['Rev'] += safe_float(row['Sale_Price'])
        stats[g]['Prof'] += safe_float(row['Profit'])

    print(f"\n{'GROUP':<15} {'STOCK':<5} {'VALUE':<10} {'REVENUE':<10} {'PROFIT'}")
    print("-" * 60)
    for g, d in stats.items():
        if d['Rev'] > 0 or d['Stock'] > 0:
            print(f"{g[:15]:<15} {d['Stock']:<5} ${d['Val']:<9.0f} ${d['Rev']:<9.0f} ${d['Prof']:.0f}")
    print("-" * 60)
    input("\nPress Enter...")

def view_todays_sales():
    print_header("TODAY'S PACKING LIST")
    today_str = date.today().strftime("%m/%d/%Y")
    sales = load_csv(SALES_FILE)
    
    found = False
    print(f"\n{'BRAND':<15} {'ITEM':<20} {'SIZE':<5} {'PRICE'}")
    print("-" * 50)
    for row in sales:
        if row['Date'] == today_str:
            item_desc = f"{row['Type']} {row['Color']}"
            print(f"{row['Brand']:<15} {item_desc:<20} {row['Size']:<5} ${row['Sale_Price']}")
            found = True
    if not found:
        print("No sales recorded today.")
    input("\nPress Enter to return...")

def view_inventory():
    inventory = load_csv(INVENTORY_FILE)
    
    # Calculate Total Value
    total_inventory_value = 0.0
    for row in inventory:
        total_inventory_value += int(row['Quantity']) * safe_float(row['WAC_Cost'])

    # Build Structure
    data = {}
    for row in inventory:
        b = row['Brand']
        t = row['Type']
        c = row['Color']
        if b not in data: data[b] = {}
        if t not in data[b]: data[b][t] = {}
        if c not in data[b][t]: data[b][t][c] = []
        data[b][t][c].append(row)

    print_header(f"CURRENT INVENTORY (Total Value: ${total_inventory_value:,.2f})")
    
    # Header Row
    print(f"{'COLOR':<15} {'TYPE':<12} {'SIZES':<45} {'VALUE'}")
    print("=" * 85)

    # Sort Brands
    sorted_brands = sorted(data.keys(), key=lambda x: get_group_rank(x, ""))

    final_group_order = []
    
    # 1. Essentials Sweats
    if "ESSENTIALS" in data:
        final_group_order.append(("ESSENTIALS", ["HOODIE", "PANT"]))
        final_group_order.append(("ESSENTIALS", ["TEE", "SHORTS"]))
    
    # 2. Others
    for b in sorted_brands:
        if b == "ESSENTIALS": continue
        final_group_order.append((b, None)) 

    for brand_key, type_filter in final_group_order:
        has_data = False
        if brand_key in data:
            if type_filter:
                for t in type_filter:
                    if t in data[brand_key]: has_data = True
            else:
                has_data = True
        
        if not has_data: continue

        header_name = brand_key
        if brand_key == "ESSENTIALS":
            if "HOODIE" in type_filter: header_name = "ESSENTIALS (Sweats)"
            else: header_name = "ESSENTIALS (Tees/Shorts)"
            
        print(f"\n[{header_name}]")
        print("-" * 85)

        available_types = list(data[brand_key].keys())
        if type_filter:
            available_types = [t for t in available_types if t in type_filter]
        
        available_types.sort()

        for type_ in available_types:
            colors = sorted(data[brand_key][type_].keys(), key=lambda c: get_color_rank(brand_key, c))
            
            for color in colors:
                items = data[brand_key][type_][color]
                group_val = 0.0
                qty_map = {row['Size']: int(row['Quantity']) for row in items}
                cost_map = {row['Size']: safe_float(row['WAC_Cost']) for row in items}
                
                valid_sizes = SIZE_MAP.get(brand_key, ["S", "M", "L"])
                
                size_parts = []
                for size in valid_sizes:
                    qty = qty_map.get(size, 0)
                    cost = cost_map.get(size, 0)
                    if qty > 0: group_val += (qty * cost)
                    size_parts.append(f"{size}({qty})")
                
                size_str = "".join([f"{s:<8}" for s in size_parts])
                
                print(f"{color:<15} {type_:<12} {size_str:<45} [${group_val:,.0f}]")

    print("-" * 85)
    input("\nPress Enter to return...")

def fix_inventory_item():
    print_header("FIX / EDIT STOCK")
    brands = list(SIZE_MAP.keys())
    brand = get_selection("Brand:", brands, "Custom")
    if not brand: return
    
    brand_types = BRAND_TYPES.get(brand, [])
    type_ = get_selection("Type:", brand_types, "Custom")
    if not type_: return
    
    color = get_selection("Color:", BRAND_COLORS.get(brand, []), "Custom")
    if not color: return
    
    inventory = load_csv(INVENTORY_FILE)
    found_items = [] 
    
    print(f"\n[STATS] Current Stock for {brand} {type_} {color}:")
    print("-" * 30)
    for i, row in enumerate(inventory):
        if (row['Brand'] == brand and row['Type'] == type_ and row['Color'] == color):
            print(f"   Size {row['Size']}: {row['Quantity']} (Cost: ${row['WAC_Cost']})")
            found_items.append((i, row['Size'], row['Quantity']))
    print("-" * 30)

    if not found_items:
        print("[X] No items found.")
        return

    print("\nWhat do you want to fix?")
    print("1. Quantity (Size specific)")
    print("2. WAC Cost (Global for this Group)")
    mode = input("Select: ").strip()
    
    if mode == '1':
        target_size = input("Enter Size to Edit: ").strip().upper()
        target_idx = -1
        for idx, size, qty in found_items:
            if size == target_size:
                target_idx = idx
                break
        if target_idx == -1:
            print("[X] Size not found.")
            return
        
        new_qty = get_valid_float(f"Enter NEW Quantity for {target_size}: ")
        if new_qty is None: return
        
        if confirm_action("Update Quantity?") == "SAVE":
            inventory[target_idx]['Quantity'] = str(int(new_qty))
            save_csv(INVENTORY_FILE, INVENTORY_COLUMNS, inventory)
            print("[OK] Updated.")
            
    elif mode == '2':
        wac_group = find_wac_group(brand, type_)
        print(f"\n[!] Updating Cost for Group: {wac_group}")
        new_cost = get_valid_float("Enter NEW Correct WAC Cost: $")
        if new_cost is None: return
        
        if confirm_action(f"Update ALL items in {wac_group} to ${new_cost}?") == "SAVE":
            count = 0
            for row in inventory:
                row_group = row.get('WAC_Group')
                if not row_group: row_group = find_wac_group(row['Brand'], row['Type'])
                if row_group == wac_group:
                    row['WAC_Cost'] = str(new_cost)
                    count += 1
            save_csv(INVENTORY_FILE, INVENTORY_COLUMNS, inventory)
            print(f"[OK] Updated cost for {count} items.")

# --- ORDER MANAGEMENT ---
def manage_orders_menu():
    print_header("ORDER MANAGEMENT")
    while True:
        print("1. View All Orders")
        print("2. View Order Details")
        print("3. Edit Payment / Status / Delete")
        print("0. Back")
        opt = input("Select: ").strip()
        
        if opt == '0' or opt == '': return
        elif opt == '1': view_all_orders()
        elif opt == '2': view_order_details()
        elif opt == '3': edit_order()

def view_all_orders():
    orders = load_csv(ORDERS_FILE)
    if not orders:
        print("No orders found.")
        return
    
    display_data = {}
    for r in orders:
        oid = r['Order_ID']
        cost = safe_float(r['Total_Cost'])
        status = r['Status']
        
        if oid not in display_data:
            display_data[oid] = {
                'Date': r['Date'],
                'Supplier': r['Supplier'],
                'Groups': {r['WAC_Group']},
                'Total_Cost': 0.0,
                'Status': status
            }
        
        display_data[oid]['Total_Cost'] += cost
        display_data[oid]['Groups'].add(r['WAC_Group'])
        if status != 'Received': display_data[oid]['Status'] = status

    sorted_oids = sorted(display_data.keys(), key=lambda x: int(x), reverse=True)
    
    print("\n--- ALL ORDERS (Consolidated) ---")
    print(f"{'ID':<5} {'DATE':<12} {'SUPPLIER':<15} {'ITEMS':<20} {'TOTAL':<10} {'STATUS'}")
    print("-" * 80)
    for oid in sorted_oids:
        d = display_data[oid]
        groups = list(d['Groups'])
        if len(groups) > 1:
            group_str = f"{len(groups)} Items (Multi)"
        else:
            group_str = groups[0][:18]
        print(f"#{oid:<4} {d['Date']:<12} {d['Supplier'][:15]:<15} {group_str:<20} ${d['Total_Cost']:<9.0f} {d['Status']}")
    print("-" * 80)
    input("\nPress Enter...")

def view_order_details():
    oid = input("\nEnter Order ID: ").strip()
    orders = load_csv(ORDERS_FILE)
    order_lines = [r for r in orders if r['Order_ID'] == oid]
    if not order_lines:
        print("Order not found.")
        return
        
    print_header(f"ORDER #{oid} DETAILS")
    first = order_lines[0]
    print("--- [ SUMMARY ] ---")
    print_aligned("Supplier:", first.get('Supplier', ''))
    print_aligned("Date:", first.get('Date', 'N/A'))
    
    grand_total = sum(safe_float(r['Total_Cost']) for r in order_lines)
    total_paid = sum(safe_float(r['Amount_Paid']) for r in order_lines)
    
    print("\n--- [ ITEMS ] ---")
    for i, r in enumerate(order_lines):
        print(f"{i+1}. {r['WAC_Group']:<20} {r['Total_Pieces']}pcs   Cost: ${safe_float(r['Total_Cost']):,.2f}  ({r['Status']})")

    print("\n--- [ FINANCIALS ] ---")
    print_aligned("Total Order Cost:", f"${grand_total:,.2f}")
    print_aligned("Total Paid:", f"${total_paid:,.2f}")
    print_aligned("Balance Due:", f"${grand_total - total_paid:,.2f}")
    input("\nPress Enter...")

def edit_order():
    orders = load_csv(ORDERS_FILE)
    active_orders = [o for o in orders if o['Status'] != 'Received']
    unique_ids = sorted(list(set(r['Order_ID'] for r in active_orders)), key=lambda x: int(x), reverse=True)
    
    print("\n--- EDITABLE ORDERS ---")
    print(", ".join(unique_ids) if unique_ids else "None")
            
    oid = input("\nEnter Order ID to Edit: ").strip()
    target_indices = [i for i, r in enumerate(orders) if r['Order_ID'] == oid]
    
    if not target_indices:
        print("Order not found.")
        return
        
    print(f"\nEditing Order #{oid}")
    print("1. DELETE ORDER (Full or Partial)")
    print("2. Update Payment (Proportional)")
    opt = input("Select: ").strip()
    
    if opt == '1':
        print("\n--- DELETION MENU ---")
        print("1. DELETE ENTIRE ORDER (All Items)")
        print("2. DELETE SPECIFIC ITEM (Partial)")
        del_opt = input("Select: ").strip()
        
        if del_opt == '1':
            confirm = input(f"PERMANENTLY DELETE Order #{oid}? (yes/no): ").lower()
            if confirm == 'yes':
                # Check if refund needed
                total_paid = sum(safe_float(orders[i]['Amount_Paid']) for i in target_indices)
                if total_paid > 0:
                    refund = input(f"Refund ${total_paid:.2f} to Cash? (y/n): ").lower()
                    if refund == 'y':
                        update_cash_on_hand(total_paid) # Add back to cash
                        print("Refund processed.")

                orders = [r for r in orders if r['Order_ID'] != oid]
                save_csv(ORDERS_FILE, ORDER_COLUMNS, orders)
                print("Order deleted successfully.")
        
        elif del_opt == '2':
            current_lines = [orders[i] for i in target_indices]
            for i, r in enumerate(current_lines):
                print(f"{i+1}. {r['WAC_Group']} (${r['Total_Cost']})")
            
            sel = input("Select Item # to Delete: ")
            if sel.isdigit() and 1 <= int(sel) <= len(current_lines):
                index_to_remove = target_indices[int(sel)-1]
                
                # Check refund for single item
                paid_amt = safe_float(orders[index_to_remove]['Amount_Paid'])
                if paid_amt > 0:
                    refund = input(f"Refund ${paid_amt:.2f} to Cash? (y/n): ").lower()
                    if refund == 'y':
                        update_cash_on_hand(paid_amt)
                        print("Refund processed.")

                del orders[index_to_remove]
                save_csv(ORDERS_FILE, ORDER_COLUMNS, orders)
                print("Item removed from order.")

    elif opt == '2':
        current_lines = [orders[i] for i in target_indices]
        grand_total = sum(safe_float(r['Total_Cost']) for r in current_lines)
        current_paid = sum(safe_float(r['Amount_Paid']) for r in current_lines)
        
        print(f"Total Cost: ${grand_total:.2f}")
        print(f"Currently Paid: ${current_paid:.2f}")
        
        new_total_paid = get_valid_float("Enter NEW Total Amount Paid: $")
        if new_total_paid is not None:
            # Financial Update
            diff = new_total_paid - current_paid
            if diff != 0:
                update_cash_on_hand(-diff) # Subtract difference (if paid more, cash goes down)
                print(f"[FINANCE] Cash adjusted by ${-diff:.2f}")

            for idx in target_indices:
                row = orders[idx]
                cost = safe_float(row['Total_Cost'])
                if grand_total > 0:
                    share = cost / grand_total
                    new_line_paid = new_total_paid * share
                else:
                    new_line_paid = 0
                
                row['Amount_Paid'] = str(round(new_line_paid, 2))
                if new_line_paid >= cost: row['Payment_Status'] = "Paid"
                elif new_line_paid == 0: row['Payment_Status'] = "Unpaid"
                else: row['Payment_Status'] = "Partial"
            
            save_csv(ORDERS_FILE, ORDER_COLUMNS, orders)
            print("Payments updated.")

def main_menu():
    while True:
        print("\n=== THREDVAULT MANAGER ===")
        print("1. Create Purchase Order (Multi-Brand)")
        print("2. Receive Stock")
        print("3. Record Sale")
        print("4. View Inventory")
        print("5. View Monthly Performance (Auto)")
        print("6. View Brand Performance")
        print("7. CEO Dashboard (Liquidity/Custom)")
        print("8. Fix Stock / Cost")
        print("9. View Today's Sales")
        print("a. Order Management")
        print("b. Sales & Returns Management")
        print("0. Exit & Save")
        
        choice = input("Select: ").strip().lower()
        if choice == '1': create_purchase_order()
        elif choice == '2': receive_stock()
        elif choice == '3': record_sale()
        elif choice == '4': view_inventory()
        elif choice == '5': view_monthly_performance()
        elif choice == '6': view_brand_performance()
        elif choice == '7': view_dashboard_menu()
        elif choice == '8': fix_inventory_item()
        elif choice == '9': view_todays_sales()
        elif choice == 'a': manage_orders_menu()
        elif choice == 'b': manage_sales_menu()
        elif choice == '0' or choice == '': 
            create_backup()
            print("Exiting...")
            break
        else: print("Invalid choice.")

if __name__ == "__main__":
    main_menu()