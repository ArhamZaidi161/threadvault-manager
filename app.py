import csv
import os
from datetime import date

# --- CONFIGURATION ---
INVENTORY_FILE = 'inventory.csv'
SALES_FILE = 'sales.csv'
ORDERS_FILE = 'orders.csv'

# I define the column headers here so they are consistent across the app
INVENTORY_COLUMNS = ["Brand", "Type", "Color", "Size", "Quantity", "WAC_Cost"]
SALES_COLUMNS = ["Date", "Brand", "Type", "Color", "Size", "Sale_Price", "Profit"]
ORDER_COLUMNS = ["Order_ID", "WAC_Group", "Supplier", "Total_Pieces", "Total_Cost", "Unit_Cost", "Status"]

# --- HELPER FUNCTIONS ---

def get_valid_float(prompt):
    # I use this to make sure I don't crash the app by typing text when it needs a number
    while True:
        try:
            value = float(input(prompt).strip())
            if value < 0:
                print("Value cannot be negative.")
                continue
            return value
        except ValueError:
            print("Please enter a valid number.")

def load_csv(filename):
    # I use this to read my files into a list of dictionaries
    if not os.path.exists(filename):
        return []
    with open(filename, mode='r') as file:
        return list(csv.DictReader(file))

def save_csv(filename, columns, data):
    # I use this to write my data back to the file
    with open(filename, mode='w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(data)

# --- MAIN FEATURES ---

def create_purchase_order():
    print("\n--- STEP 1: CREATE PURCHASE ORDER ---")
    # I enter the details from my Order sheet (e.g., Order 21, Den_HoodiePant)
    
    order_id = input("Order ID (e.g. 21): ").strip()
    wac_group = input("WAC Group (e.g. Den_HoodiePant): ").strip()
    supplier = input("Supplier (e.g. Jake): ").strip()
    
    total_pieces = int(get_valid_float("Total Pieces in this Group: "))
    total_cost = get_valid_float("Total Cost for this Group ($): ")
    
    # I automatically calculate the per-piece cost so I don't have to do it later
    if total_pieces > 0:
        unit_cost = total_cost / total_pieces
    else:
        unit_cost = 0.0
        
    print(f"Calculated Unit Cost: ${unit_cost:.2f}")

    # I append this new order to my orders file
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
    print(f"Order {order_id} ({wac_group}) saved.")

def receive_stock():
    print("\n--- STEP 2: RECEIVE STOCK ---")
    # I use this when the box actually arrives at my house
    
    order_id = input("Enter Order ID to receive: ").strip()
    
    # I load the orders to find matching groups
    all_orders = load_csv(ORDERS_FILE)
    matching_orders = []
    
    # I find all rows that match this ID (because Order 21 might have 3 different brands)
    for i, row in enumerate(all_orders):
        if row['Order_ID'] == order_id:
            matching_orders.append((i, row))
            
    if not matching_orders:
        print("Order ID not found.")
        return

    # I display the groups so I can choose which one I'm unboxing
    print(f"\nFound {len(matching_orders)} groups in Order {order_id}:")
    for idx, (original_index, row) in enumerate(matching_orders):
        print(f"{idx + 1}. {row['WAC_Group']} (Cost: ${row['Unit_Cost']}/ea)")
        
    choice = int(get_valid_float("Select Group to receive (1, 2, etc): ")) - 1
    
    if choice < 0 or choice >= len(matching_orders):
        print("Invalid selection.")
        return

    # I grab the specific cost for this group
    selected_index, selected_order = matching_orders[choice]
    unit_cost = float(selected_order['Unit_Cost'])
    
    print(f"\nReceiving {selected_order['WAC_Group']} at cost ${unit_cost:.2f}")
    
    # Now I enter the specific items (Brand, Color, Sizes)
    brand = input("Brand: ").strip().upper()
    type_ = input("Type: ").strip().upper()
    color = input("Color: ").strip().upper()
    
    inventory = load_csv(INVENTORY_FILE)
    
    while True:
        size = input("\nEnter Size (or 'DONE'): ").strip().upper()
        if size == 'DONE':
            break
            
        qty_received = int(get_valid_float("Quantity Received: "))
        
        # I check if this item exists to calculate the new Weighted Average Cost
        found = False
        for row in inventory:
            if (row['Brand'] == brand and row['Type'] == type_ and 
                row['Color'] == color and row['Size'] == size):
                
                # I grab the old numbers
                old_qty = int(row['Quantity'])
                old_wac = float(row['WAC_Cost'])
                
                # THE WAC MATH: ((OldQty * OldCost) + (NewQty * NewCost)) / TotalQty
                total_value = (old_qty * old_wac) + (qty_received * unit_cost)
                total_qty = old_qty + qty_received
                new_wac = total_value / total_qty
                
                # I update the row
                row['Quantity'] = str(total_qty)
                row['WAC_Cost'] = str(round(new_wac, 2))
                print(f"Updated: {size} now has {total_qty} units @ ${new_wac:.2f} WAC")
                found = True
                break
        
        # If it's a new item, I just add it with the current unit cost
        if not found:
            inventory.append({
                "Brand": brand, "Type": type_, "Color": color, "Size": size,
                "Quantity": str(qty_received),
                "WAC_Cost": str(round(unit_cost, 2))
            })
            print(f"Added: {size} (New SKU)")

    # I save the inventory updates
    save_csv(INVENTORY_FILE, INVENTORY_COLUMNS, inventory)
    
    # I mark the order as Received in the orders file
    all_orders[selected_index]['Status'] = "Received"
    save_csv(ORDERS_FILE, ORDER_COLUMNS, all_orders)
    print("Stock updated and Order marked as received.")

def record_sale():
    print("\n--- STEP 3: RECORD SALE ---")
    # I use this when I sell something
    
    brand = input("Brand: ").strip().upper()
    color = input("Color: ").strip().upper()
    size = input("Size: ").strip().upper()
    
    inventory = load_csv(INVENTORY_FILE)
    found_item = None
    
    # I search for the item
    for row in inventory:
        if (row['Brand'] == brand and row['Color'] == color and row['Size'] == size):
            found_item = row
            break
            
    if not found_item:
        print("Item not found in inventory.")
        return
        
    current_qty = int(found_item['Quantity'])
    if current_qty <= 0:
        print("Error: Stock is 0.")
        return

    # I enter the sale price
    sale_price = get_valid_float("Sale Price: $")
    
    # I calculate profit using the WAC stored in the inventory row
    cost = float(found_item['WAC_Cost'])
    profit = sale_price - cost
    
    # I update the inventory count
    found_item['Quantity'] = str(current_qty - 1)
    save_csv(INVENTORY_FILE, INVENTORY_COLUMNS, inventory)
    
    # I log the sale
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
    print("\n--- MANUAL ENTRY (DAY 1 SETUP) ---")
    # I use this to add my existing stock without needing an Order ID
    
    brand = input("Brand: ").strip().upper()
    type_ = input("Type: ").strip().upper()
    color = input("Color: ").strip().upper()
    size = input("Size: ").strip().upper()
    qty = int(get_valid_float("Quantity in hand: "))
    wac = get_valid_float("Current WAC Cost ($): ")
    
    inventory = load_csv(INVENTORY_FILE)
    
    # I assume this is a new entry since it's Day 1, but I check duplicates just in case
    inventory.append({
        "Brand": brand, "Type": type_, "Color": color, "Size": size,
        "Quantity": str(qty), "WAC_Cost": str(wac)
    })
    
    save_csv(INVENTORY_FILE, INVENTORY_COLUMNS, inventory)
    print("Manual entry saved.")

def view_inventory():
    print("\n--- CURRENT INVENTORY ---")
    inventory = load_csv(INVENTORY_FILE)
    if not inventory:
        print("Inventory is empty.")
    else:
        print(f"{'BRAND':<15} {'COLOR':<15} {'SIZE':<5} {'QTY':<5} {'WAC'}")
        print("-" * 50)
        for row in inventory:
            # Only show if I have stock
            if int(row['Quantity']) > 0:
                print(f"{row['Brand']:<15} {row['Color']:<15} {row['Size']:<5} {row['Quantity']:<5} ${float(row['WAC_Cost']):.2f}")

def main_menu():
    while True:
        print("\n=== THREDVAULT MANAGER ===")
        print("1. Create Purchase Order (From Order Sheet)")
        print("2. Receive Stock (Updates WAC)")
        print("3. Record Sale (Tracks Profit)")
        print("4. Manual Entry (Initial Setup)")
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
            print("Saving and exiting...")
            break
        else:
            print("Invalid choice.")

if __name__ == "__main__":
    main_menu()