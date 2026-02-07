# main.py
import os
from datetime import datetime, date
import database as db
import utils as ut
import models as md

# --- CORE FEATURES ---

def create_purchase_order():
    ut.print_header("CREATE PURCHASE ORDER (Multi-Brand)")
    new_order_id = db.get_next_order_id()
    print(f"Generated Order ID: #{new_order_id}")
    
    supplier = input("Supplier Name: ").strip()
    if not supplier: return
    
    date_str = input(f"Order Date (Enter for Today {date.today().strftime('%m/%d/%Y')}): ").strip()
    if not date_str: date_str = date.today().strftime("%m/%d/%Y")

    cart = [] 

    while True:
        print(f"\n--- Adding Item #{len(cart)+1} to Order #{new_order_id} ---")
        wac_group = ut.get_selection("Select Brand/Category Group:", md.VALID_WAC_GROUPS, "Add Custom")
        if not wac_group: break 

        pcs = ut.get_valid_float(f"Pieces for {wac_group}: ")
        if pcs is None: continue
        
        line_cost = ut.get_valid_float(f"Total Cost for these {int(pcs)} pcs ($): ")
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
        print(f"{i+1}. {item['WAC_Group']:<20} {int(item['Total_Pieces'])}pcs    ${item['Total_Cost']:,.2f}")
    print("-" * 40)
    ut.print_aligned("TOTAL COST:", f"${grand_total_cost:,.2f}")
    
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
        total_paid = ut.get_valid_float("Total Amount Paid Upfront: $")
        if total_paid is None: return
        payment_status = "Partial"
    
    remaining_balance = grand_total_cost - total_paid
    if remaining_balance > 0:
        print(f"[!] Remaining Balance to Pay: ${remaining_balance:,.2f}")

    if ut.confirm_action(f"Save Order #{new_order_id} with {len(cart)} items?") == "SAVE":
        existing_orders = db.load_csv(md.ORDERS_FILE)
        
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
        
        db.save_csv(md.ORDERS_FILE, md.ORDER_COLUMNS, existing_orders)
        
        # --- FINANCIAL UPDATE ---
        if total_paid > 0:
            new_cash = db.update_cash_on_hand(-total_paid)
            print(f"[FINANCE] Cash updated: -${total_paid:.2f} (Bal: ${new_cash:.2f})")
            
        print(f"Order #{new_order_id} Saved Successfully!")

def receive_stock():
    ut.print_header("RECEIVE STOCK")
    all_orders = db.load_csv(md.ORDERS_FILE)
    
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
    unit_cost = ut.safe_float(target_row['Unit_Cost'])
    
    print(f"\nReceiving: {wac_group}")
    print(f"Cost Basis: ${unit_cost:.2f}/unit")
    
    brand = md.WAC_TO_BRAND.get(wac_group, "UNKNOWN")
    allowed_types = md.WAC_TO_TYPES.get(wac_group, [])
    
    if brand == "UNKNOWN":
        brand = input("Enter Brand Name: ").strip().upper()
    
    while True:
        if len(allowed_types) == 1:
            type_ = allowed_types[0]
            print(f"Type: {type_}")
            single_type = True
        elif allowed_types:
            type_ = ut.get_selection(f"Select Type for {brand}:", allowed_types, "Custom")
            single_type = False
        else:
            type_ = input("Enter Type: ").strip().upper()
            single_type = False
            
        if not type_: break

        while True:
            colors = md.BRAND_COLORS.get(brand, [])
            color = ut.get_selection(f"Color for {type_}:", colors, "Custom")
            if not color: break
            
            valid_sizes = md.SIZE_MAP.get(brand, ["S", "M", "L"])
            staged = []
            
            print(f"\n--- Batch Entry: {brand} {type_} {color} ---")
            for size in valid_sizes:
                q = ut.get_valid_float(f"  Qty {size}: ", True)
                if q is None: break
                if q > 0: staged.append((size, int(q)))
            
            if staged:
                inventory = db.load_csv(md.INVENTORY_FILE)
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
                db.save_csv(md.INVENTORY_FILE, md.INVENTORY_COLUMNS, inventory)
                db.recalculate_global_wac(wac_group)
                print("  Saved Batch.")
                
            print(f"Finished {color}. Add another Color?")
        
        if single_type: break
        else: print(f"Finished {type_}. Add another Type?")

    close = input(f"Mark {wac_group} (Order #{order_id}) as Received? (y/n): ").lower()
    if close == 'y':
        current_data = db.load_csv(md.ORDERS_FILE)
        for r in current_data:
            if r['Order_ID'] == order_id and r['WAC_Group'] == wac_group and r['Status'] != 'Received':
                r['Status'] = "Received"
                break
        db.save_csv(md.ORDERS_FILE, md.ORDER_COLUMNS, current_data)
        print("Item Closed.")

def record_sale():
    ut.print_header("RECORD SALE")
    brands = list(md.SIZE_MAP.keys())
    brand = ut.get_selection("Brand:", brands, "Custom")
    if not brand: return

    brand_types = md.BRAND_TYPES.get(brand, [])
    type_ = ut.get_selection("Type:", brand_types, "Custom")
    if not type_: return

    colors = md.BRAND_COLORS.get(brand, [])
    color = ut.get_selection("Color:", colors, "Custom")
    if not color: return

    sizes = md.SIZE_MAP.get(brand, ["S", "M", "L"])
    size = ut.get_selection("Size:", sizes, "Custom")
    if not size: return

    inventory = db.load_csv(md.INVENTORY_FILE)
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
    price = ut.get_valid_float("Sale Price: $")
    if price is None: return

    cost = ut.safe_float(found_item['WAC_Cost'])
    profit = price - cost
    wac_grp = found_item.get('WAC_Group', 'UNKNOWN')

    if ut.confirm_action(f"Sell 1x for ${price:.2f} (Profit: ${profit:.2f})") == "SAVE":
        found_item['Quantity'] = str(int(found_item['Quantity']) - 1)
        db.save_csv(md.INVENTORY_FILE, md.INVENTORY_COLUMNS, inventory)
        
        sales = db.load_csv(md.SALES_FILE)
        new_sale_id = db.get_next_sale_id()
        sales.append({
            "ID": new_sale_id,
            "Date": date.today().strftime("%m/%d/%Y"),
            "Brand": brand, "Type": type_, "Color": color, "Size": size,
            "Sale_Price": str(price), "Profit": str(round(profit, 2)),
            "WAC_Group": wac_grp
        })
        db.save_csv(md.SALES_FILE, md.SALES_COLUMNS, sales)
        
        new_cash = db.update_cash_on_hand(price)
        print(f"[FINANCE] Cash added: +${price:.2f} (Bal: ${new_cash:.2f})")
        print("Sale Recorded!")

def manage_sales_menu():
    ut.print_header("SALES & RETURNS MANAGEMENT")
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
    sales = db.load_csv(md.SALES_FILE)
    if not sales:
        print("No sales records.")
        return
    
    print(f"\n{'ID':<4} {'DATE':<10} {'ITEM':<35} {'PRICE':<10}")
    print("-" * 65)
    for row in sales[-10:]:
        desc = f"{row['Brand']} {row['Type']} {row['Color']} {row['Size']}"
        print(f"#{row['ID']:<3} {row['Date']:<10} {desc[:35]:<35} ${ut.safe_float(row['Sale_Price']):.2f}")
    input("\nPress Enter...")

def edit_sale_price():
    sale_id = input("Enter Sale ID to Edit: ").strip()
    sales = db.load_csv(md.SALES_FILE)
    
    target_idx = -1
    for i, r in enumerate(sales):
        if r['ID'] == sale_id:
            target_idx = i
            break
    
    if target_idx == -1:
        print("Sale ID not found.")
        return
        
    sale = sales[target_idx]
    old_price = ut.safe_float(sale['Sale_Price'])
    print(f"Current Price: ${old_price:.2f}")
    
    new_price = ut.get_valid_float("Enter New Correct Price: $")
    if new_price is not None:
        diff = new_price - old_price
        db.update_cash_on_hand(diff)
        
        sale['Sale_Price'] = str(new_price)
        cost = old_price - ut.safe_float(sale['Profit']) 
        sale['Profit'] = str(new_price - cost)
        
        db.save_csv(md.SALES_FILE, md.SALES_COLUMNS, sales)
        print(f"Updated. Cash adjusted by ${diff:.2f}.")

def process_return():
    print("\n--- PROCESS RETURN ---")
    sale_id = input("Enter Sale ID to Return: ").strip()
    sales = db.load_csv(md.SALES_FILE)
    
    target_idx = -1
    for i, r in enumerate(sales):
        if r['ID'] == sale_id:
            target_idx = i
            break
    
    if target_idx == -1:
        print("Sale ID not found.")
        return
        
    sale = sales[target_idx]
    refund_amount = ut.safe_float(sale['Sale_Price'])
    
    print(f"Returning: {sale['Brand']} {sale['Type']} {sale['Color']} {sale['Size']}")
    print(f"Refund Amount: ${refund_amount:.2f}")
    
    if ut.confirm_action("Confirm Return & Refund?") == "SAVE":
        new_cash = db.update_cash_on_hand(-refund_amount)
        print(f"[FINANCE] Refunded ${refund_amount:.2f} (Bal: ${new_cash:.2f})")
        
        inventory = db.load_csv(md.INVENTORY_FILE)
        found = False
        for row in inventory:
            if (row['Brand'] == sale['Brand'] and row['Type'] == sale['Type'] and 
                row['Color'] == sale['Color'] and row['Size'] == sale['Size']):
                row['Quantity'] = str(int(row['Quantity']) + 1)
                found = True
                break
        
        if not found:
            cost_basis = refund_amount - ut.safe_float(sale['Profit'])
            inventory.append({
                "Brand": sale['Brand'], "Type": sale['Type'], "Color": sale['Color'],
                "Size": sale['Size'], "Quantity": "1", 
                "WAC_Cost": str(cost_basis), "WAC_Group": sale['WAC_Group']
            })
        
        db.save_csv(md.INVENTORY_FILE, md.INVENTORY_COLUMNS, inventory)
        print("[INVENTORY] Item restocked.")
        
        del sales[target_idx]
        db.save_csv(md.SALES_FILE, md.SALES_COLUMNS, sales)
        print("[SALES] Record removed.")

def view_dashboard_menu():
    ut.print_header("CEO DASHBOARD")
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

    sales = db.load_csv(md.SALES_FILE)
    rev = 0.0
    profit = 0.0
    units = 0
    
    for row in sales:
        try:
            s_date = datetime.strptime(row['Date'], "%m/%d/%Y").date()
            if start_dt <= s_date <= end_dt:
                rev += ut.safe_float(row['Sale_Price'])
                profit += ut.safe_float(row['Profit'])
                units += 1
        except: continue
        
    margin = (profit / rev * 100) if rev > 0 else 0.0
    
    print("-" * 30)
    ut.print_aligned("Period:", f"{start_str} to {end_str}")
    ut.print_aligned("Revenue:", f"${rev:,.2f}")
    ut.print_aligned("Profit:", f"${profit:,.2f}")
    ut.print_aligned("Gross Margin:", f"{margin:.2f}%")
    ut.print_aligned("Units Sold:", f"{units}")
    print("-" * 30)
    input("\nPress Enter...")

def dashboard_liquidity():
    ut.print_header("LIQUIDITY & LIFETIME")
    fin = db.load_financials()
    
    ut.print_aligned("Cash on Hand:", f"${fin.get('Cash_On_Hand', 0):,.2f}")
    ut.print_aligned("Outstanding:", f"${fin.get('Outstanding_Payables', 0):,.2f}")
    
    update = input("\nUpdate these values? (y/n): ").lower()
    
    if update == 'y':
        val = ut.get_valid_float("New Cash Balance (Enter to skip): $", True)
        if val is not None:
            fin['Cash_On_Hand'] = val
        pay = ut.get_valid_float("New Outstanding Payables (Enter to skip): $", True)
        if pay is not None:
            fin['Outstanding_Payables'] = pay
        db.save_financials(fin['Cash_On_Hand'], fin['Outstanding_Payables'])

    orders = db.load_csv(md.ORDERS_FILE)
    committed_cash = 0.0
    total_bought_qty = 0
    
    for row in orders:
        if row['Status'] != 'Cancelled':
            cost = ut.safe_float(row.get('Total_Cost'))
            paid = ut.safe_float(row.get('Amount_Paid'))
            committed_cash += (cost - paid)
            total_bought_qty += int(row.get('Total_Pieces', 0))

    inventory = db.load_csv(md.INVENTORY_FILE)
    on_hand_val = 0.0
    for row in inventory:
        on_hand_val += (int(row['Quantity']) * ut.safe_float(row['WAC_Cost']))

    sales = db.load_csv(md.SALES_FILE)
    lifetime_rev = 0.0
    lifetime_profit = 0.0
    lifetime_sold = 0
    for row in sales:
        lifetime_rev += ut.safe_float(row['Sale_Price'])
        lifetime_profit += ut.safe_float(row['Profit'])
        lifetime_sold += 1

    net_worth = fin['Cash_On_Hand'] + on_hand_val - committed_cash
    
    print("\n" + "="*35)
    print("FINANCIAL SNAPSHOT")
    ut.print_aligned("Cash on Hand:", f"${fin['Cash_On_Hand']:,.2f}")
    ut.print_aligned("Outstanding:", f"${committed_cash:,.2f}")
    ut.print_aligned("Available Cash:", f"${(fin['Cash_On_Hand'] - committed_cash):,.2f}")
    ut.print_aligned("Stock Value:", f"${on_hand_val:,.2f}")
    ut.print_aligned("Net Worth:", f"${net_worth:,.2f}")
    
    print("\nLIFETIME TOTALS")
    ut.print_aligned("Total Revenue:", f"${lifetime_rev:,.2f}")
    ut.print_aligned("Total Profit:", f"${lifetime_profit:,.2f}")
    ut.print_aligned("Sold / Bought:", f"{lifetime_sold} / {total_bought_qty}")
    if lifetime_sold > 0:
        ut.print_aligned("Avg Rev/Pc:", f"${lifetime_rev/lifetime_sold:,.2f}")
        ut.print_aligned("Avg Prof/Pc:", f"${lifetime_profit/lifetime_sold:,.2f}")
    print("="*35)
    input("\nPress Enter...")

def view_brand_performance():
    ut.print_header("BRAND PERFORMANCE")
    stats = {}
    
    inv = db.load_csv(md.INVENTORY_FILE)
    for row in inv:
        g = row.get('WAC_Group', 'UNKNOWN')
        if g not in stats: stats[g] = {'Stock':0, 'Val':0.0, 'Rev':0.0, 'Prof':0.0}
        q = int(row['Quantity'])
        stats[g]['Stock'] += q
        stats[g]['Val'] += (q * ut.safe_float(row['WAC_Cost']))
        
    sales = db.load_csv(md.SALES_FILE)
    for row in sales:
        g = row.get('WAC_Group', 'UNKNOWN')
        if not g or g == 'None':
            g = md.find_wac_group(row['Brand'], row['Type'])
            
        if g not in stats: stats[g] = {'Stock':0, 'Val':0.0, 'Rev':0.0, 'Prof':0.0}
        stats[g]['Rev'] += ut.safe_float(row['Sale_Price'])
        stats[g]['Prof'] += ut.safe_float(row['Profit'])

    print(f"\n{'GROUP':<15} {'STOCK':<5} {'VALUE':<10} {'REVENUE':<10} {'PROFIT'}")
    print("-" * 60)
    for g, d in stats.items():
        if d['Rev'] > 0 or d['Stock'] > 0:
            print(f"{g[:15]:<15} {d['Stock']:<5} ${d['Val']:<9.0f} ${d['Rev']:<9.0f} ${d['Prof']:.0f}")
    print("-" * 60)
    input("\nPress Enter...")

def view_todays_sales():
    ut.print_header("TODAY'S PACKING LIST")
    today_str = date.today().strftime("%m/%d/%Y")
    sales = db.load_csv(md.SALES_FILE)
    
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
    inventory = db.load_csv(md.INVENTORY_FILE)
    
    total_inventory_value = 0.0
    for row in inventory:
        total_inventory_value += int(row['Quantity']) * ut.safe_float(row['WAC_Cost'])

    data = {}
    for row in inventory:
        b = row['Brand']
        t = row['Type']
        c = row['Color']
        if b not in data: data[b] = {}
        if t not in data[b]: data[b][t] = {}
        if c not in data[b][t]: data[b][t][c] = []
        data[b][t][c].append(row)

    ut.print_header(f"CURRENT INVENTORY (Total Value: ${total_inventory_value:,.2f})")
    
    print(f"{'COLOR':<15} {'TYPE':<12} {'SIZES':<45} {'VALUE'}")
    print("=" * 85)

    sorted_brands = sorted(data.keys(), key=lambda x: md.get_group_rank(x, ""))

    final_group_order = []
    
    if "ESSENTIALS" in data:
        final_group_order.append(("ESSENTIALS", ["HOODIE", "PANT"]))
        final_group_order.append(("ESSENTIALS", ["TEE", "SHORTS"]))
    
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
            colors = sorted(data[brand_key][type_].keys(), key=lambda c: md.get_color_rank(brand_key, c))
            
            for color in colors:
                items = data[brand_key][type_][color]
                group_val = 0.0
                qty_map = {row['Size']: int(row['Quantity']) for row in items}
                cost_map = {row['Size']: ut.safe_float(row['WAC_Cost']) for row in items}
                
                valid_sizes = md.SIZE_MAP.get(brand_key, ["S", "M", "L"])
                
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
    ut.print_header("FIX / EDIT STOCK")
    brands = list(md.SIZE_MAP.keys())
    brand = ut.get_selection("Brand:", brands, "Custom")
    if not brand: return
    
    brand_types = md.BRAND_TYPES.get(brand, [])
    type_ = ut.get_selection("Type:", brand_types, "Custom")
    if not type_: return
    
    color = ut.get_selection("Color:", md.BRAND_COLORS.get(brand, []), "Custom")
    if not color: return
    
    inventory = db.load_csv(md.INVENTORY_FILE)
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
        
        new_qty = ut.get_valid_float(f"Enter NEW Quantity for {target_size}: ")
        if new_qty is None: return
        
        if ut.confirm_action("Update Quantity?") == "SAVE":
            inventory[target_idx]['Quantity'] = str(int(new_qty))
            db.save_csv(md.INVENTORY_FILE, md.INVENTORY_COLUMNS, inventory)
            print("[OK] Updated.")
            
    elif mode == '2':
        wac_group = md.find_wac_group(brand, type_)
        print(f"\n[!] Updating Cost for Group: {wac_group}")
        new_cost = ut.get_valid_float("Enter NEW Correct WAC Cost: $")
        if new_cost is None: return
        
        if ut.confirm_action(f"Update ALL items in {wac_group} to ${new_cost}?") == "SAVE":
            count = 0
            for row in inventory:
                row_group = row.get('WAC_Group')
                if not row_group: row_group = md.find_wac_group(row['Brand'], row['Type'])
                if row_group == wac_group:
                    row['WAC_Cost'] = str(new_cost)
                    count += 1
            db.save_csv(md.INVENTORY_FILE, md.INVENTORY_COLUMNS, inventory)
            print(f"[OK] Updated cost for {count} items.")

def manage_orders_menu():
    ut.print_header("ORDER MANAGEMENT")
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
    orders = db.load_csv(md.ORDERS_FILE)
    if not orders:
        print("No orders found.")
        return
    
    display_data = {}
    for r in orders:
        oid = r['Order_ID']
        cost = ut.safe_float(r['Total_Cost'])
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
    orders = db.load_csv(md.ORDERS_FILE)
    order_lines = [r for r in orders if r['Order_ID'] == oid]
    if not order_lines:
        print("Order not found.")
        return
        
    ut.print_header(f"ORDER #{oid} DETAILS")
    first = order_lines[0]
    print("--- [ SUMMARY ] ---")
    ut.print_aligned("Supplier:", first.get('Supplier', ''))
    ut.print_aligned("Date:", first.get('Date', 'N/A'))
    
    grand_total = sum(ut.safe_float(r['Total_Cost']) for r in order_lines)
    total_paid = sum(ut.safe_float(r['Amount_Paid']) for r in order_lines)
    
    print("\n--- [ ITEMS ] ---")
    for i, r in enumerate(order_lines):
        print(f"{i+1}. {r['WAC_Group']:<20} {r['Total_Pieces']}pcs    Cost: ${ut.safe_float(r['Total_Cost']):,.2f}  ({r['Status']})")

    print("\n--- [ FINANCIALS ] ---")
    ut.print_aligned("Total Order Cost:", f"${grand_total:,.2f}")
    ut.print_aligned("Total Paid:", f"${total_paid:,.2f}")
    ut.print_aligned("Balance Due:", f"${grand_total - total_paid:,.2f}")
    input("\nPress Enter...")

def edit_order():
    orders = db.load_csv(md.ORDERS_FILE)
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
                total_paid = sum(ut.safe_float(orders[i]['Amount_Paid']) for i in target_indices)
                if total_paid > 0:
                    refund = input(f"Refund ${total_paid:.2f} to Cash? (y/n): ").lower()
                    if refund == 'y':
                        db.update_cash_on_hand(total_paid) 
                        print("Refund processed.")

                orders = [r for r in orders if r['Order_ID'] != oid]
                db.save_csv(md.ORDERS_FILE, md.ORDER_COLUMNS, orders)
                print("Order deleted successfully.")
        
        elif del_opt == '2':
            current_lines = [orders[i] for i in target_indices]
            for i, r in enumerate(current_lines):
                print(f"{i+1}. {r['WAC_Group']} (${r['Total_Cost']}) - Paid: ${r['Amount_Paid']}")
            
            sel = input("Select Item # to Delete: ")
            if sel.isdigit() and 1 <= int(sel) <= len(current_lines):
                item_to_delete = current_lines[int(sel)-1]
                index_to_remove = target_indices[int(sel)-1]
                
                paid_amt = ut.safe_float(item_to_delete['Amount_Paid'])
                if paid_amt > 0:
                    print(f"You have paid ${paid_amt:.2f} for this item.")
                    refund = input("Did you get a refund for this specific item? (y/n): ").lower()
                    if refund == 'y':
                        db.update_cash_on_hand(paid_amt)
                        print(f"[FINANCE] refunded ${paid_amt:.2f} to cash.")

                del orders[index_to_remove]
                db.save_csv(md.ORDERS_FILE, md.ORDER_COLUMNS, orders)
                print("Item removed from order.")

    elif opt == '2':
        current_lines = [orders[i] for i in target_indices]
        grand_total = sum(ut.safe_float(r['Total_Cost']) for r in current_lines)
        current_paid = sum(ut.safe_float(r['Amount_Paid']) for r in current_lines)
        
        print(f"Total Cost: ${grand_total:.2f}")
        print(f"Currently Paid: ${current_paid:.2f}")
        
        new_total_paid = ut.get_valid_float("Enter NEW Total Amount Paid: $")
        if new_total_paid is not None:
            diff = new_total_paid - current_paid
            if diff != 0:
                db.update_cash_on_hand(-diff)
                print(f"[FINANCE] Cash adjusted by ${-diff:.2f}")

            for idx in target_indices:
                row = orders[idx]
                cost = ut.safe_float(row['Total_Cost'])
                if grand_total > 0:
                    share = cost / grand_total
                    new_line_paid = new_total_paid * share
                else:
                    new_line_paid = 0
                
                row['Amount_Paid'] = str(round(new_line_paid, 2))
                if new_line_paid >= cost: row['Payment_Status'] = "Paid"
                elif new_line_paid == 0: row['Payment_Status'] = "Unpaid"
                else: row['Payment_Status'] = "Partial"
            
            db.save_csv(md.ORDERS_FILE, md.ORDER_COLUMNS, orders)
            print("Payments updated.")

if __name__ == "__main__":
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
            db.create_backup()
            print("Exiting...")
            break
        else: print("Invalid choice.")