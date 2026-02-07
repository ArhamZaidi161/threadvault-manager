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

INVENTORY_COLUMNS = ["Brand", "Type", "Color", "Size", "Quantity", "WAC_Cost", "WAC_Group"]
SALES_COLUMNS = ["Date", "Brand", "Type", "Color", "Size", "Sale_Price", "Profit"]
ORDER_COLUMNS = ["Order_ID", "WAC_Group", "Supplier", "Total_Pieces", "Total_Cost", "Unit_Cost", "Status"]

VALID_WAC_GROUPS = [
    "Ess_HoodiePant", "Ess_TeeShort", "Spdr_HoodiePant", "Den_HoodiePant", "Eric_EmanShorts"
]

WAC_TO_BRAND = {
    "Ess_HoodiePant": "ESSENTIALS", "Ess_TeeShort": "ESSENTIALS",
    "Spdr_HoodiePant": "SP5DER", "Den_HoodiePant": "DENIM TEARS",
    "Eric_EmanShorts": "ERIC EMANUEL"
}

WAC_TO_TYPES = {
    "Ess_HoodiePant": ["HOODIE", "PANT"], "Ess_TeeShort": ["TEE", "SHORTS"],
    "Spdr_HoodiePant": ["HOODIE", "PANT"], "Den_HoodiePant": ["HOODIE", "PANT"],
    "Eric_EmanShorts": ["SHORTS"]
}

BRAND_TYPES = {
    "ESSENTIALS": ["HOODIE", "PANT", "TEE", "SHORTS"],
    "SP5DER": ["HOODIE", "PANT"],
    "DENIM TEARS": ["HOODIE", "PANT"],
    "ERIC EMANUEL": ["SHORTS"]
}

SIZE_SORT_ORDER = {
    "XXS": 0, "XS": 1, "S": 2, "M": 3, "L": 4, "XL": 5, "XXL": 6, "ONE SIZE": 99
}

SIZE_MAP = {
    "ESSENTIALS": ["XS", "S", "M", "L"],
    "SP5DER": ["S", "M", "L"],
    "DENIM TEARS": ["S", "M", "L"],
    "ERIC EMANUEL": ["XS", "S", "M", "L", "XL"]
}

BRAND_COLORS = {
    "ESSENTIALS": ["BLACK", "B22", "L/O", "D/O", "1977 D/O", "1977 IRON"],
    "SP5DER": ["BLACK", "PINK", "BLUE"],
    "DENIM TEARS": ["GREY", "BLACK"],
    "ERIC EMANUEL": ["BLACK", "NAVY", "GREY", "LIGHT BLUE", "RED", "WHITE"]
}

# --- HELPER FUNCTIONS ---

def create_backup():
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    files = [INVENTORY_FILE, SALES_FILE, ORDERS_FILE]
    for f in files:
        if os.path.exists(f):
            shutil.copy2(f, os.path.join(BACKUP_DIR, f"{f}_{timestamp}.bak"))

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
        if choice == '0' or choice == 'BACK': return None
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(options): return options[idx]
            elif custom_label and idx == len(options):
                val = input(f"Enter {custom_label}: ").strip().upper()
                return val if val else None 
        if choice in options: return choice
        if custom_label and not choice.isdigit(): return choice
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
    for row in orders:
        try:
            cid = int(row['Order_ID'])
            if cid > max_id: max_id = cid
        except: continue
    return str(max_id + 1)

def find_wac_group(brand, type_):
    for group, types in WAC_TO_TYPES.items():
        mapped_brand = WAC_TO_BRAND.get(group)
        if mapped_brand == brand and type_ in types:
            return group
    return "UNKNOWN"

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
            c = float(row['WAC_Cost'])
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
            data = {row[0]: float(row[1]) for row in reader}
        return data
    except:
        return defaults

def save_financials(cash, payables):
    with open(FINANCIALS_FILE, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Cash_On_Hand", cash])
        writer.writerow(["Outstanding_Payables", payables])

# --- FEATURES ---

def create_purchase_order():
    while True:
        print("\n--- CREATE PURCHASE ORDER ---")
        new_order_id = get_next_order_id()
        print(f"New Order ID: #{new_order_id}")
        supplier = input("Supplier Name (or 'c' to cancel): ").strip()
        if supplier.lower() == 'c': return

        try:
            num_groups_in = input("How many different Brands/Groups in this order? ")
            if num_groups_in.lower() == 'c': return
            num_groups = int(num_groups_in)
        except ValueError:
            print("Invalid number.")
            continue

        staged_orders = []
        for i in range(num_groups):
            print(f"\n--- Group {i+1}/{num_groups} ---")
            wac_group = get_selection("Select WAC Group:", VALID_WAC_GROUPS, "Add Custom")
            if not wac_group: return 
            pcs = get_valid_float(f"Total Pieces for {wac_group}: ")
            if pcs is None: return
            cost = get_valid_float(f"Total Cost for {wac_group} ($): ")
            if cost is None: return
            unit = cost / pcs if pcs > 0 else 0
            
            staged_orders.append({
                "Order_ID": new_order_id, "WAC_Group": wac_group, "Supplier": supplier,
                "Total_Pieces": str(int(pcs)), "Total_Cost": str(cost),
                "Unit_Cost": str(round(unit, 2)), "Status": "Ordered"
            })

        summary = f"Supplier: {supplier}\nItems:\n"
        for o in staged_orders:
            summary += f" - {o['WAC_Group']}: {o['Total_Pieces']} pcs @ ${o['Unit_Cost']}/ea\n"
        
        action = confirm_action(summary)
        if action == "SAVE":
            existing = load_csv(ORDERS_FILE)
            existing.extend(staged_orders)
            save_csv(ORDERS_FILE, ORDER_COLUMNS, existing)
            print("Saved!")
            break
        elif action == "CANCEL": break

def receive_stock():
    print("\n--- RECEIVE STOCK ---")
    all_orders = load_csv(ORDERS_FILE)
    pending_ids = {} 
    for row in all_orders:
        if row['Status'] == 'Ordered':
            oid = row['Order_ID']
            if oid not in pending_ids:
                pending_ids[oid] = {'Supplier': row['Supplier'], 'Groups': 0}
            pending_ids[oid]['Groups'] += 1
            
    if not pending_ids:
        print("No pending orders found.")
        return

    print("\nPENDING ORDERS:")
    order_list = list(pending_ids.keys())
    for i, oid in enumerate(order_list):
        info = pending_ids[oid]
        print(f"{i + 1}. Order #{oid} | {info['Supplier']} | {info['Groups']} Groups pending")
        
    choice = get_valid_float("Select Order # to Receive: ")
    if choice is None: return
    choice = int(choice) - 1
    if choice < 0 or choice >= len(order_list): return

    target_order_id = order_list[choice]
    
    while True:
        all_orders = load_csv(ORDERS_FILE)
        order_groups = []
        for i, row in enumerate(all_orders):
            if row['Order_ID'] == target_order_id and row['Status'] == 'Ordered':
                order_groups.append((i, row))
        
        if not order_groups:
            print("All groups in this order have been received!")
            return

        print(f"\n--- Processing Order #{target_order_id} ---")
        current_index, current_row = order_groups[0]
        wac_group = current_row['WAC_Group']
        unit_cost = float(current_row['Unit_Cost'])
        
        print(f"Current Group: {wac_group} (Cost: ${unit_cost:.2f}/ea)")
        proceed = input("Receive this group now? (y/n - n skips to next group): ").lower()
        if proceed != 'y':
            print("Skipping remaining items in this order.")
            return

        brand = WAC_TO_BRAND.get(wac_group, "UNKNOWN")
        allowed_types = WAC_TO_TYPES.get(wac_group, [])
        if brand == "UNKNOWN":
            brand = input("Brand not detected. Enter Brand: ").strip().upper()
            if not brand: return
        else: print(f"Brand identified: {brand}")

        while True:
            if len(allowed_types) == 1:
                type_ = allowed_types[0]
                print(f"Auto-selected Type: {type_}")
                single_type_mode = True
            elif allowed_types:
                type_ = get_selection(f"Select Type for {brand}:", allowed_types, custom_label="Add New Type")
                single_type_mode = False
            else:
                type_ = input("Enter Type: ").strip().upper()
                single_type_mode = False
            if not type_: break 

            while True:
                brand_colors = BRAND_COLORS.get(brand, ["BLACK", "WHITE"])
                color = get_selection(f"Select Color for {type_}:", brand_colors, custom_label="Add New Color")
                if not color: break

                valid_sizes = SIZE_MAP.get(brand, ["S", "M", "L"])
                staged_items = []
                print(f"\n--- BATCH ENTRY: {brand} {type_} {color} ---")
                print("Enter quantity for each size (Press Enter to skip/0)")
                
                for size in valid_sizes:
                    qty = get_valid_float(f"  Qty {size}: ", allow_empty_as_zero=True)
                    if qty is None: break 
                    if qty > 0: staged_items.append((size, int(qty)))

                while True:
                    add_custom = input("  Add outlier/custom size? (y/n): ").lower()
                    if add_custom != 'y': break
                    cust_size = input("    Enter Size: ").strip().upper()
                    cust_qty = get_valid_float(f"    Qty {cust_size}: ")
                    if cust_qty and cust_qty > 0: staged_items.append((cust_size, int(cust_qty)))

                if staged_items:
                    print("\n  Review Batch:")
                    for s, q in staged_items: print(f"   - {s}: {q}")
                    conf = input("  Confirm? (y/n): ").lower()
                    
                    if conf == 'y':
                        inventory = load_csv(INVENTORY_FILE)
                        for size, qty in staged_items:
                            found = False
                            for row in inventory:
                                if (row['Brand'] == brand and row['Type'] == type_ and 
                                    row['Color'] == color and row['Size'] == size):
                                    old_qty = int(row['Quantity'])
                                    new_total = old_qty + qty
                                    row['Quantity'] = str(new_total)
                                    row['WAC_Group'] = wac_group
                                    found = True
                                    break
                            if not found:
                                inventory.append({
                                    "Brand": brand, "Type": type_, "Color": color, "Size": size,
                                    "Quantity": str(qty), "WAC_Cost": str(unit_cost), "WAC_Group": wac_group
                                })
                        save_csv(INVENTORY_FILE, INVENTORY_COLUMNS, inventory)
                        recalculate_global_wac(wac_group)
                    else:
                        print("  Batch cancelled. Re-enter.")
                        continue 

                print(f"\nFinished {color}. Add another Color for {type_}?")

            if single_type_mode: break 
            else: print(f"\nFinished {type_}. Add another Type for {brand} (e.g. Pant)?")

        confirm = input(f"\nFinished receiving {wac_group}? Mark as CLOSED? (y/n): ").lower()
        if confirm == 'y':
            all_orders[current_index]['Status'] = "Received"
            save_csv(ORDERS_FILE, ORDER_COLUMNS, all_orders)
            print("Group marked as closed.")
        else: print("Group left open (Partial Receive).")
        
        remaining = len(order_groups) - 1
        if remaining > 0:
            cont = input(f"\nThere are {remaining} other groups in Order #{target_order_id}. Continue? (y/n): ").lower()
            if cont != 'y': return
        else: return

def record_sale():
    while True:
        print("\n--- RECORD SALE ---")
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
            continue 

        if int(found_item['Quantity']) <= 0:
            print("Stock is 0! Cannot sell.")
            continue

        print(f"Found: {brand} {type_} {color} {size} (Stock: {found_item['Quantity']})")
        price = get_valid_float("Sale Price: $")
        if price is None: return

        cost = float(found_item['WAC_Cost'])
        profit = price - cost

        summary = f"Selling: {brand} {type_} {size}\nPrice: ${price}\nEst. Profit: ${profit:.2f}"
        action = confirm_action(summary)

        if action == "SAVE":
            found_item['Quantity'] = str(int(found_item['Quantity']) - 1)
            save_csv(INVENTORY_FILE, INVENTORY_COLUMNS, inventory)
            sales = load_csv(SALES_FILE)
            sales.append({
                "Date": date.today().strftime("%m/%d/%Y"),
                "Brand": brand, "Type": type_, "Color": color, "Size": size,
                "Sale_Price": str(price), "Profit": str(round(profit, 2))
            })
            save_csv(SALES_FILE, SALES_COLUMNS, sales)
            print("Sale Recorded!")
            return
        elif action == "CANCEL": return

def manual_entry():
    while True:
        print("\n--- MANUAL ENTRY ---")
        brand = get_selection("Brand:", list(SIZE_MAP.keys()), "Custom")
        if not brand: return

        last_type = None
        current_wac = None

        while True:
            # Type Loop
            brand_types = BRAND_TYPES.get(brand, [])
            if len(brand_types) == 1:
                type_ = brand_types[0]
                print(f"Auto-selected Type: {type_}")
                single_type_mode = True
            elif brand_types:
                type_ = get_selection("Type:", brand_types, "Custom")
                single_type_mode = False
            else:
                type_ = input("Type: ").strip().upper()
                single_type_mode = False
            
            if not type_: break

            wac_group = find_wac_group(brand, type_)
            print(f"Detected WAC Group: {wac_group}")

            if type_ == last_type and current_wac is not None:
                print(f"Using previous WAC for {type_}: ${current_wac}")
            else:
                wac_input = input(f"WAC Cost for {brand} {type_} (Press Enter for $0 or type value): $")
                if wac_input.strip() == "": current_wac = 0.0
                elif wac_input.upper() == 'CANCEL': break
                else:
                    try: current_wac = float(wac_input)
                    except ValueError:
                        print("Invalid cost. Skipping type.")
                        continue
            
            last_type = type_

            while True:
                # Color Loop
                colors = BRAND_COLORS.get(brand, [])
                color = get_selection(f"Color for {type_}:", colors, "Custom")
                if not color: break

                valid_sizes = SIZE_MAP.get(brand, ["S", "M", "L"])
                staged_items = []

                print(f"\n--- BATCH ENTRY: {brand} {type_} {color} ---")
                for size in valid_sizes:
                    qty = get_valid_float(f"  Qty {size}: ", allow_empty_as_zero=True)
                    if qty is None: break
                    if qty > 0: staged_items.append((size, int(qty)))

                while True:
                    add_custom = input("  Add outlier/custom size? (y/n): ").lower()
                    if add_custom != 'y': break
                    cust_size = input("    Enter Size: ").strip().upper()
                    cust_qty = get_valid_float(f"    Qty {cust_size}: ")
                    if cust_qty and cust_qty > 0: staged_items.append((cust_size, int(cust_qty)))

                if staged_items:
                    print("\n  REVIEW BATCH:")
                    for s, q in staged_items: print(f"   - {s}: {q}")
                    conf = input("  Confirm? (y/n): ").lower()
                    
                    if conf == 'y':
                        inventory = load_csv(INVENTORY_FILE)
                        for size, qty in staged_items:
                            found = False
                            for row in inventory:
                                if (row['Brand'] == brand and row['Type'] == type_ and 
                                    row['Color'] == color and row['Size'] == size):
                                    row['Quantity'] = str(int(qty) + int(row.get('Quantity', 0))) 
                                    row['WAC_Cost'] = str(current_wac)
                                    row['WAC_Group'] = wac_group
                                    found = True
                                    break
                            if not found:
                                inventory.append({
                                    "Brand": brand, "Type": type_, "Color": color, "Size": size,
                                    "Quantity": str(qty), "WAC_Cost": str(current_wac), "WAC_Group": wac_group
                                })
                        save_csv(INVENTORY_FILE, INVENTORY_COLUMNS, inventory)
                        if wac_group != "UNKNOWN": recalculate_global_wac(wac_group)
                        print("  ✅ Saved.")
                    else:
                        print("  ❌ Cancelled. Re-enter this color.")
                        continue

                print(f"\nFinished {color}. Add another Color for {type_}?")
            
            if single_type_mode: break
            else: print(f"\nFinished {type_}. Add another Type for {brand}?")

def fix_inventory_item():
    """Corrects Quantity OR Global Cost."""
    print("\n--- FIX / EDIT STOCK ---")
    brands = list(SIZE_MAP.keys())
    brand = get_selection("Brand:", brands, "Custom")
    if not brand: return
    
    brand_types = BRAND_TYPES.get(brand, [])
    type_ = get_selection("Type:", brand_types, "Custom")
    if not type_: return
    
    color = get_selection("Color:", BRAND_COLORS.get(brand, []), "Custom")
    if not color: return
    
    # 1. SHOW CURRENT STOCK
    inventory = load_csv(INVENTORY_FILE)
    found_items = [] 
    current_wac = "0.00"
    
    print(f"\n📊 Current Stock for {brand} {type_} {color}:")
    print("-" * 30)
    for i, row in enumerate(inventory):
        if (row['Brand'] == brand and row['Type'] == type_ and row['Color'] == color):
            print(f"   Size {row['Size']}: {row['Quantity']} (Cost: ${row['WAC_Cost']})")
            found_items.append((i, row['Size'], row['Quantity']))
            current_wac = row['WAC_Cost']
    print("-" * 30)

    if not found_items:
        print("❌ No items found.")
        return

    # 2. SELECT FIX MODE
    print("\nWhat do you want to fix?")
    print("1. Quantity (Size specific)")
    print("2. WAC Cost (Global for this Group)")
    mode = input("Select: ").strip()
    
    if mode == '1':
        # FIX QUANTITY
        target_size = input("Enter Size to Edit: ").strip().upper()
        target_idx = -1
        current_qty = 0
        
        for idx, size, qty in found_items:
            if size == target_size:
                target_idx = idx
                current_qty = qty
                break
                
        if target_idx == -1:
            print("❌ Size not found.")
            return
            
        new_qty = get_valid_float(f"Enter NEW Quantity for {target_size} (was {current_qty}): ")
        if new_qty is None: return
        
        confirm = input(f"Change {target_size} stock to {int(new_qty)}? (y/n): ").lower()
        if confirm == 'y':
            inventory[target_idx]['Quantity'] = str(int(new_qty))
            save_csv(INVENTORY_FILE, INVENTORY_COLUMNS, inventory)
            print("✅ Stock updated.")
            
    elif mode == '2':
        # FIX GLOBAL COST
        wac_group = find_wac_group(brand, type_)
        print(f"\n⚠️  Updating Cost for Group: {wac_group}")
        print(f"   Current Cost: ${current_wac}")
        
        new_cost = get_valid_float("   Enter NEW Correct WAC Cost: $")
        if new_cost is None: return
        
        confirm = input(f"Update ALL items in {wac_group} to ${new_cost}? (y/n): ").lower()
        if confirm == 'y':
            # Iterate entire inventory and update match groups
            count = 0
            for row in inventory:
                row_group = row.get('WAC_Group')
                if not row_group: row_group = find_wac_group(row['Brand'], row['Type'])
                
                if row_group == wac_group:
                    row['WAC_Cost'] = str(new_cost)
                    count += 1
            save_csv(INVENTORY_FILE, INVENTORY_COLUMNS, inventory)
            print(f"✅ Updated cost for {count} items.")

def view_financials():
    print("\n--- CEO DASHBOARD ---")
    
    fin_data = load_financials()
    saved_cash = fin_data.get("Cash_On_Hand", 0.0)
    saved_payables = fin_data.get("Outstanding_Payables", 0.0)
    
    print(f"Saved Cash on Hand: ${saved_cash:,.2f}")
    print(f"Saved Payables:     ${saved_payables:,.2f}")
    update = input("Update these values? (y/n): ").lower()
    
    if update == 'y':
        cash_hand = get_valid_float("Enter New Cash on Hand: $")
        if cash_hand is None: return
        payables = get_valid_float("Enter New Outstanding Payables: $")
        if payables is None: return
        save_financials(cash_hand, payables)
    else:
        cash_hand = saved_cash
        payables = saved_payables

    inventory = load_csv(INVENTORY_FILE)
    on_hand_val = 0.0
    brand_profit = {} 
    
    for row in inventory:
        q = int(row['Quantity'])
        c = float(row['WAC_Cost'])
        if q > 0: on_hand_val += (q * c)
            
    orders = load_csv(ORDERS_FILE)
    in_transit_val = 0.0
    for row in orders:
        if row['Status'] == 'Ordered':
            in_transit_val += float(row['Total_Cost'])

    sales = load_csv(SALES_FILE)
    total_sales = 0.0
    total_profit = 0.0
    
    for row in sales:
        p = float(row['Profit'])
        total_profit += p
        total_sales += float(row['Sale_Price'])
        b = row['Brand']
        brand_profit[b] = brand_profit.get(b, 0.0) + p

    total_committed_stock = on_hand_val + in_transit_val
    available_cash = cash_hand - payables
    net_worth = cash_hand + on_hand_val - payables
    
    if brand_profit:
        top_brand = max(brand_profit, key=brand_profit.get)
        top_val = brand_profit[top_brand]
    else:
        top_brand = "N/A"
        top_val = 0.0

    print("\n" + "="*30)
    print(f"FINANCIAL SNAPSHOT")
    print("="*30)
    print(f"Cash on Hand:            ${cash_hand:,.2f}")
    print(f"Outstanding Payables:    ${payables:,.2f}")
    print("-" * 30)
    print(f"Available Cash:          ${available_cash:,.2f}")
    print(f"On-Hand Inventory:       ${on_hand_val:,.2f}")
    print(f"In-Transit Inventory:    ${in_transit_val:,.2f}")
    print(f"Total Committed to Stock:${total_committed_stock:,.2f}")
    print("-" * 30)
    print(f"NET WORTH (Est):         ${net_worth:,.2f}")
    print(f"Top Brand (Profit):      {top_brand} (${top_val:,.2f})")
    input("\nPress Enter to return...")

def view_todays_sales():
    print("\n--- TODAY'S PACKING LIST ---")
    today_str = date.today().strftime("%m/%d/%Y")
    sales = load_csv(SALES_FILE)
    
    found = False
    print(f"{'BRAND':<15} {'ITEM':<20} {'SIZE':<5} {'PRICE'}")
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
    inventory.sort(key=lambda x: (
        x['Brand'], 
        x['Type'], 
        x['Color'], 
        SIZE_SORT_ORDER.get(x['Size'], 99)
    ))
    
    print(f"\n{'BRAND':<15} {'TYPE':<12} {'COLOR':<12} {'SIZE':<6} {'QTY':<5} {'COST':<10} {'VALUE'}")
    print("=" * 80)
    
    prev_item_key = None 

    for row in inventory:
        q = int(row['Quantity'])
        if q > 0:
            wac = float(row['WAC_Cost'])
            val = q * wac
            
            # Identify "Item Group" by Brand/Type/Color
            current_item_key = (row['Brand'], row['Type'], row['Color'])
            
            # Add separator line if item group changes
            if prev_item_key is not None and current_item_key != prev_item_key:
                print("-" * 80)

            print(f"{row['Brand']:<15} {row['Type']:<12} {row['Color']:<12} {row['Size']:<6} {q:<5} ${wac:<9.2f} ${val:,.2f}")
            
            prev_item_key = current_item_key
    
    print("=" * 80)
    input("\nPress Enter to return...")

def main_menu():
    while True:
        print("\n=== THREDVAULT MANAGER ===")
        print("1. Create Purchase Order")
        print("2. Receive Stock")
        print("3. Record Sale")
        print("4. Manual Entry")
        print("5. View Inventory")
        print("6. CEO Dashboard")
        print("7. Fix / Edit Stock Count")
        print("8. View Today's Sales")
        print("9. Exit & Save")
        
        choice = input("Select: ").strip()
        if choice == '1': create_purchase_order()
        elif choice == '2': receive_stock()
        elif choice == '3': record_sale()
        elif choice == '4': manual_entry()
        elif choice == '5': view_inventory()
        elif choice == '6': view_financials()
        elif choice == '7': fix_inventory_item()
        elif choice == '8': view_todays_sales()
        elif choice == '9': 
            create_backup()
            print("Exiting...")
            break
        else: print("Invalid choice.")

if __name__ == "__main__":
    main_menu()