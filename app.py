import csv
import os
from datetime import date

# --- CONFIGURATION ---
INVENTORY_FILE = 'inventory.csv'
SALES_FILE = 'sales.csv'
ORDERS_FILE = 'orders.csv'

# I use these columns to ensure my files always have the correct headers
INVENTORY_COLUMNS = ["Brand", "Type", "Color", "Size", "Quantity", "WAC_Cost"]
SALES_COLUMNS = ["Date", "Brand", "Type", "Color", "Size", "Sale_Price", "Profit"]
ORDER_COLUMNS = ["Order_ID", "WAC_Group", "Supplier", "Total_Pieces", "Total_Cost", "Unit_Cost", "Status"]

# --- SMART LISTS (The "Brain" of the App) ---

# 1. WAC GROUPS: These are the financial buckets I use in my Orders
VALID_WAC_GROUPS = [
    "Ess_HoodiePant",
    "Ess_TeeShort",
    "Spdr_HoodiePant",
    "Den_HoodiePant",
    "Eric_EmanShorts"
]

# 2. BRAND MAPPING: When I select a WAC Group, the App knows the Brand automatically
WAC_TO_BRAND = {
    "Ess_HoodiePant": "ESSENTIALS",
    "Ess_TeeShort": "ESSENTIALS",
    "Spdr_HoodiePant": "SP5DER",
    "Den_HoodiePant": "DENIM TEARS",
    "Eric_EmanShorts": "ERIC EMANUEL"
}

# 3. TYPE RESTRICTIONS: When I select a WAC Group, the App knows what TYPES are allowed
WAC_TO_TYPES = {
    "Ess_HoodiePant": ["HOODIE", "PANT"],
    "Ess_TeeShort": ["TEE", "SHORTS"],
    "Spdr_HoodiePant": ["HOODIE", "PANT"],
    "Den_HoodiePant": ["HOODIE", "PANT"],
    "Eric_EmanShorts": ["SHORTS"]
}

# 4. SIZE RULES: The App knows which sizes exist for which brand
SIZE_MAP = {
    "ESSENTIALS": ["XS", "S", "M", "L"],
    "SP5DER": ["S", "M", "L"],
    "DENIM TEARS": ["S", "M", "L"],
    "ERIC EMANUEL": ["XS", "S", "M", "L", "XL"]
}

# 5. COLORS: The standard colors I trade in
VALID_COLORS = [
    "BLACK", "L/O", "D/O", "B22", "PINK", "BLUE", "RED", "NAVY", "GREY"
]

# --- HELPER FUNCTIONS ---

def get_valid_float(prompt):
    # I use this to stop the app from crashing if I type letters instead of numbers
    while True:
        try:
            value = float(input(prompt).strip())
            if value < 0:
                print("Value cannot be negative.")
                continue
            return value
        except ValueError:
            print("Please enter a valid number.")

def get_selection(prompt, options, allow_custom=False):
    # I use this to force myself to pick from a list so I don't make typos
    print(f"\n{prompt}")
    for i, opt in enumerate(options):
        print(f"{i + 1}. {opt}")
    
    if allow_custom:
        print(f"{len(options) + 1}. [Type Custom Value]")

    while True:
        choice = input("Select option # (or type value): ").strip().upper()
        
        # If I typed a number
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(options):
                return options[idx]
            elif allow_custom and idx == len(options):
                return input("Enter custom value: ").strip().upper()
        
        # If I typed the text directly (e.g. "BLACK")
        if choice in options:
            return choice
            
        # If I typed a custom word and custom is allowed
        if allow_custom and not choice.isdigit():
             return choice

        print("Invalid selection. Please pick a number from the list.")

def load_csv(filename):
    if not os.path.exists(filename):
        return []
    with open(filename, mode='r') as file:
        return list(csv.DictReader(file))

def save_csv(filename, columns, data):
    with open(filename, mode='w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(data)

# --- MAIN FEATURES ---

def create_purchase_order():
    print("\n--- STEP 1: CREATE PURCHASE ORDER ---")
    
    order_id = input("Order ID (e.g. 21): ").strip()
    
    # I select the WAC Group from my preset list to avoid typos
    wac_group = get_selection("Select WAC Group:", VALID_WAC_GROUPS, allow_custom=False)
    
    supplier = input("Supplier Name: ").strip()
    
    total_pieces = int(get_valid_float("Total Pieces: "))
    total_cost = get_valid_float("Total Cost ($): ")
    
    if total_pieces > 0:
        unit_cost = total_cost / total_pieces
    else:
        unit_cost = 0.0
        
    print(f"Calculated Unit Cost: ${unit_cost:.2f}")

    orders = load_csv(ORDERS_FILE)
    orders.append({
        "Order_ID": order_id,
        "WAC_Group": wac_group,
        "Supplier": supplier,
        "Total_Pieces": str(total_pieces),
        "Total_Cost": str(total_cost),
        "Unit_Cost": str(round(unit_cost, 2)),
        "Status": "Ordered"
    })
    save_csv(ORDERS_FILE, ORDER_COLUMNS, orders)
    print(f"Order {order_id} saved.")

def receive_stock():
    print("\n--- STEP 2: RECEIVE STOCK ---")
    
    order_id = input("Enter Order ID to receive: ").strip()
    
    all_orders = load_csv(ORDERS_FILE)
    matching_orders = []
    
    for i, row in enumerate(all_orders):
        if row['Order_ID'] == order_id:
            matching_orders.append((i, row))
            
    if not matching_orders:
        print("Order ID not found.")
        return

    # I choose which WAC Group from this order I am receiving
    print(f"\nFound {len(matching_orders)} groups in Order {order_id}:")
    for idx, (original_index, row) in enumerate(matching_orders):
        print(f"{idx + 1}. {row['WAC_Group']} (Cost: ${row['Unit_Cost']}/ea)")
        
    choice_idx = int(get_valid_float("Select Group # to receive: ")) - 1
    
    if choice_idx < 0 or choice_idx >= len(matching_orders):
        print("Invalid selection.")
        return

    selected_index, selected_order = matching_orders[choice_idx]
    wac_group = selected_order['WAC_Group']
    unit_cost = float(selected_order['Unit_Cost'])
    
    print(f"\nReceiving {wac_group} @ ${unit_cost:.2f}")

    # --- AUTO-INFERENCE LOGIC ---
    # The App determines Brand and valid Types based on the WAC Group
    inferred_brand = WAC_TO_BRAND.get(wac_group, "UNKNOWN")
    allowed_types = WAC_TO_TYPES.get(wac_group, [])
    
    # I set the Brand automatically
    if inferred_brand != "UNKNOWN":
        print(f"Brand identified as: {inferred_brand}")
        brand = inferred_brand
    else:
        brand = input("Enter Brand: ").strip().upper()

    # I select the Type from the allowed list (e.g., Hoodie or Pant)
    if allowed_types:
        type_ = get_selection("Select Type:", allowed_types, allow_custom=True)
    else:
        type_ = input("Enter Type: ").strip().upper()

    # I select the Color (Presets + Custom option)
    color = get_selection("Select Color:", VALID_COLORS, allow_custom=True)
    
    # I determine valid sizes based on the Brand
    valid_sizes = SIZE_MAP.get(brand, ["S", "M", "L"]) # Default to S-L if unknown
    
    inventory = load_csv(INVENTORY_FILE)
    
    # Loop to add multiple sizes for this specific Brand/Type/Color
    while True:
        size = get_selection("Select Size (or type DONE to finish):", valid_sizes, allow_custom=True)
        
        if size == 'DONE':
            break
            
        qty_received = int(get_valid_float(f"Quantity of {size} received: "))
        
        # WAC CALCULATION
        found = False
        for row in inventory:
            if (row['Brand'] == brand and row['Type'] == type_ and 
                row['Color'] == color and row['Size'] == size):
                
                old_qty = int(row['Quantity'])
                old_wac = float(row['WAC_Cost'])
                
                total_value = (old_qty * old_wac) + (qty_received * unit_cost)
                total_qty = old_qty + qty_received
                new_wac = total_value / total_qty
                
                row['Quantity'] = str(total_qty)
                row['WAC_Cost'] = str(round(new_wac, 2))
                print(f"Updated {size}: Stock {total_qty}, New WAC ${new_wac:.2f}")
                found = True
                break
        
        if not found:
            inventory.append({
                "Brand": brand, "Type": type_, "Color": color, "Size": size,
                "Quantity": str(qty_received),
                "WAC_Cost": str(round(unit_cost, 2))
            })
            print(f"Added {size}: Stock {qty_received}")

    save_csv(INVENTORY_FILE, INVENTORY_COLUMNS, inventory)
    
    # Update Order Status
    all_orders[selected_index]['Status'] = "Received"
    save_csv(ORDERS_FILE, ORDER_COLUMNS, all_orders)
    print("Stock updated successfully.")

def record_sale():
    print("\n--- STEP 3: RECORD SALE ---")
    
    # I use the same smart logic for sales to match the inventory exactly
    # Since I don't have a WAC group here, I pick Brand first
    brand_list = list(SIZE_MAP.keys()) # Get brands from my config
    brand = get_selection("Select Brand:", brand_list, allow_custom=True)
    
    # Standard colors
    color = get_selection("Select Color:", VALID_COLORS, allow_custom=True)
    
    # Standard sizes for that brand
    valid_sizes = SIZE_MAP.get(brand, ["S", "M", "L"])
    size = get_selection("Select Size:", valid_sizes, allow_custom=True)
    
    type_ = input("Enter Type (e.g. Hoodie): ").strip().upper()
    
    inventory = load_csv(INVENTORY_FILE)
    found_item = None
    
    for row in inventory:
        if (row['Brand'] == brand and row['Color'] == color and 
            row['Size'] == size and row['Type'] == type_):
            found_item = row
            break
            
    if not found_item:
        print("Item not found in inventory. Check your selection.")
        return
        
    current_qty = int(found_item['Quantity'])
    if current_qty <= 0:
        print("Error: Stock is 0.")
        return

    sale_price = get_valid_float("Sale Price: $")
    cost = float(found_item['WAC_Cost'])
    profit = sale_price - cost
    
    # Decrease Stock
    found_item['Quantity'] = str(current_qty - 1)
    save_csv(INVENTORY_FILE, INVENTORY_COLUMNS, inventory)
    
    # Log Sale
    sales = load_csv(SALES_FILE)
    sales.append({
        "Date": date.today().strftime("%m/%d/%Y"),
        "Brand": found_item['Brand'],
        "Type": found_item['Type'],
        "Color": found_item['Color'],
        "Size": found_item['Size'],
        "Sale_Price": str(sale_price),
        "Profit": str(round(profit, 2))
    })
    save_csv(SALES_FILE, SALES_COLUMNS, sales)
    
    print(f"Sold! Profit: ${profit:.2f}")

def manual_entry():
    print("\n--- MANUAL ENTRY ---")
    
    brand_list = list(SIZE_MAP.keys())
    brand = get_selection("Select Brand:", brand_list, allow_custom=True)
    type_ = input("Enter Type (e.g. Hoodie): ").strip().upper()
    color = get_selection("Select Color:", VALID_COLORS, allow_custom=True)
    
    valid_sizes = SIZE_MAP.get(brand, ["S", "M", "L"])
    size = get_selection("Select Size:", valid_sizes, allow_custom=True)
    
    qty = int(get_valid_float("Quantity in hand: "))
    wac = get_valid_float("Current WAC Cost ($): ")
    
    inventory = load_csv(INVENTORY_FILE)
    
    # Check if exists to update, otherwise add
    found = False
    for row in inventory:
        if (row['Brand'] == brand and row['Type'] == type_ and 
            row['Color'] == color and row['Size'] == size):
            
            # For manual entry, I assume I am correcting the count/cost
            row['Quantity'] = str(qty)
            row['WAC_Cost'] = str(wac)
            found = True
            print("Updated existing entry.")
            break
            
    if not found:
        inventory.append({
            "Brand": brand, "Type": type_, "Color": color, "Size": size,
            "Quantity": str(qty), "WAC_Cost": str(wac)
        })
        print("Added new entry.")
    
    save_csv(INVENTORY_FILE, INVENTORY_COLUMNS, inventory)

def view_inventory():
    print("\n--- CURRENT INVENTORY ---")
    inventory = load_csv(INVENTORY_FILE)
    if not inventory:
        print("Inventory is empty.")
    else:
        # Simple header format
        print(f"{'BRAND':<15} {'TYPE':<10} {'COLOR':<10} {'SIZE':<5} {'QTY':<5} {'WAC'}")
        print("-" * 60)
        for row in inventory:
            if int(row['Quantity']) > 0:
                print(f"{row['Brand']:<15} {row['Type']:<10} {row['Color']:<10} {row['Size']:<5} {row['Quantity']:<5} ${float(row['WAC_Cost']):.2f}")

def main_menu():
    while True:
        print("\n=== THREDVAULT MANAGER v3.0 ===")
        print("1. Create Purchase Order")
        print("2. Receive Stock (Auto-Brand/Size Logic)")
        print("3. Record Sale")
        print("4. Manual Entry / Correction")
        print("5. View Inventory")
        print("6. Exit")
        
        choice = input("Select: ").strip()
        
        if choice == '1':
            create_purchase_order()
        elif choice == '2':
            receive_stock()
        elif choice == '3':
            record_sale()
        elif choice == '4':
            manual_entry()
        elif choice == '5':
            view_inventory()
        elif choice == '6':
            print("Exiting...")
            break
        else:
            print("Invalid choice.")

if __name__ == "__main__":
    main_menu()