import streamlit as st
import pandas as pd
import database as db
import models as md
from datetime import date, datetime, timedelta
import os
import shutil

# --- CONFIGURATION ---
st.set_page_config(page_title="Thredvault Manager", layout="wide")

# --- CSV COLUMN MIGRATION (The Fix) ---
def ensure_csv_columns():
    """Checks orders.csv and adds Delivery_Date if missing."""
    if not os.path.exists(md.ORDERS_FILE): return
    
    # Read just the header
    with open(md.ORDERS_FILE, 'r') as f:
        header = f.readline().strip().split(',')
    
    # If Delivery_Date is missing, rewrite the file
    if "Delivery_Date" not in header:
        st.toast("Updating database schema... (Adding Delivery_Date)")
        # Backup first
        shutil.copy(md.ORDERS_FILE, md.ORDERS_FILE + ".bak")
        
        # Load all data
        df = pd.read_csv(md.ORDERS_FILE)
        df['Delivery_Date'] = "N/A" # Add new column
        
        # Save back
        df.to_csv(md.ORDERS_FILE, index=False)

ensure_csv_columns()

# --- SESSION STATE ---
if 'sales_cart' not in st.session_state: st.session_state.sales_cart = []
if 'purchase_cart' not in st.session_state: st.session_state.purchase_cart = []
if 'receive_cart' not in st.session_state: st.session_state.receive_cart = []

# --- CUSTOM CSS ---
st.markdown("""
<style>
    div.stMetric { background-color: #0E1117; padding: 15px; border-radius: 10px; border: 1px solid #262730; }
    .big-font { font-size: 20px !important; font-weight: bold; }
    div.stButton > button { width: 100%; border-radius: 5px; font-weight: bold; }
    .warning { color: #ffbd45; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- SORTING CONSTANTS ---
ESSENTIALS_ORDER = ["B22", "LIGHT OATMEAL", "L/O", "1977 IRON", "1977 DARK OAT", "1977 D/O", "DARK OATMEAL", "D/O", "BLACK", "WHITE"]
TYPE_ORDER = ["HOODIE", "PANT", "TEE", "SHORTS", "SLIDES"]

# --- HELPER FUNCTIONS ---
def get_custom_color_index(color):
    c = str(color).upper()
    for i, val in enumerate(ESSENTIALS_ORDER):
        if val in c: return i
    return 99

def get_type_index(type_):
    t = str(type_).upper()
    try: return TYPE_ORDER.index(t)
    except: return 99

def get_inventory_display_group(brand, type_):
    b = str(brand).upper(); t = str(type_).upper()
    if b == "ESSENTIALS":
        if t in ["HOODIE", "PANT"]: return "ESSENTIALS (Sweats)"
        return "ESSENTIALS (Tees/Shorts)"
    return b

def get_group_sort_order(group_name):
    if "ESSENTIALS (Sweats)" in group_name: return 1
    if "ESSENTIALS (Tees" in group_name: return 2
    if "DENIM TEARS" in group_name: return 3
    if "SP5DER" in group_name: return 4
    if "ERIC EMANUEL" in group_name: return 5
    if "YZY" in group_name: return 6
    return 99

def calculate_time_horizon_metrics(df, start_date, end_date):
    if df.empty: return {"Revenue": 0.0, "Profit": 0.0}
    mask = (df['Date'] >= pd.to_datetime(start_date)) & (df['Date'] <= pd.to_datetime(end_date)) & (df['Status'] == 'Completed')
    period_df = df.loc[mask]
    return {"Revenue": period_df['Sale_Price'].sum(), "Profit": period_df['Profit'].sum()}

# --- SIDEBAR ---
st.sidebar.title("🔐 Thredvault")
main_menu = st.sidebar.radio("Navigate:", 
    ["Dashboard", "Inventory", "Receive Stock", "Log Sale", "Purchasing", "Analytics", "Admin Tools"]
)

# ==============================================================================
# 1. DASHBOARD
# ==============================================================================
if main_menu == "Dashboard":
    st.title("CEO Dashboard 🚀")
    
    # Load Data
    sales_data = db.load_csv(md.SALES_FILE)
    sales_df = pd.DataFrame(sales_data)
    if not sales_df.empty:
        if 'Status' not in sales_df.columns: sales_df['Status'] = 'Completed'
        sales_df['Date'] = pd.to_datetime(sales_df['Date'])
        sales_df['Sale_Price'] = pd.to_numeric(sales_df['Sale_Price'])
        sales_df['Profit'] = pd.to_numeric(sales_df['Profit'])
    
    inv_data = db.load_csv(md.INVENTORY_FILE)
    inv_df = pd.DataFrame(inv_data) if inv_data else pd.DataFrame(columns=md.INVENTORY_COLUMNS)
    if not inv_df.empty:
        inv_df['Quantity'] = pd.to_numeric(inv_df['Quantity'])
        inv_df['WAC_Cost'] = pd.to_numeric(inv_df['WAC_Cost'])
        inv_df['Total Value'] = inv_df['Quantity'] * inv_df['WAC_Cost']

    orders_data = db.load_csv(md.ORDERS_FILE)
    orders_df = pd.DataFrame(orders_data) if orders_data else pd.DataFrame(columns=md.ORDER_COLUMNS)

    fin = db.load_financials()
    
    # --- MTD PERFORMANCE ---
    st.subheader("📅 Period Performance (Month-to-Date)")
    today = datetime.now()
    start_of_month = today.replace(day=1)
    
    if not sales_df.empty:
        mtd_mask = (sales_df['Date'] >= start_of_month) & (sales_df['Date'] <= today) & (sales_df['Status'] == 'Completed')
        mtd_df = sales_df.loc[mtd_mask]
        mtd_rev = mtd_df['Sale_Price'].sum()
        mtd_prof = mtd_df['Profit'].sum()
        mtd_units = len(mtd_df)
        mtd_margin = (mtd_prof / mtd_rev * 100) if mtd_rev > 0 else 0.0
    else: mtd_rev, mtd_prof, mtd_units, mtd_margin = 0, 0, 0, 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Revenue", f"${mtd_rev:,.2f}")
    c2.metric("Profit", f"${mtd_prof:,.2f}")
    c3.metric("Gross Margin", f"{mtd_margin:.2f}%")
    c4.metric("Units Sold", f"{mtd_units}")
    st.divider()

    # --- LIQUIDITY SNAPSHOT ---
    st.subheader("💧 Liquidity Snapshot")
    cash = fin.get('Cash_On_Hand', 0.0)
    payables = fin.get('Outstanding_Payables', 0.0)
    
    in_transit_val = 0.0
    if not orders_df.empty:
        pending = orders_df[(orders_df['Status'] != 'Received') & (orders_df['Status'] != 'Cancelled')]
        if not pending.empty: in_transit_val = pd.to_numeric(pending['Total_Cost']).sum()

    on_hand_stock_val = inv_df['Total Value'].sum() if not inv_df.empty else 0.0
    total_committed_stock = on_hand_stock_val + in_transit_val
    committed_cash = 0.0
    available_cash = cash - committed_cash
    net_worth = available_cash + total_committed_stock - payables

    l1, l2, l3 = st.columns(3)
    with l1:
        st.markdown("**Cash Position**")
        st.write(f"Cash on hand: **${cash:,.2f}**")
        st.write(f"Outstanding payables: **${payables:,.2f}**")
        st.write(f"Commited cash: **${committed_cash:,.2f}**")
        st.write(f"Available cash: **${available_cash:,.2f}**")
    with l2:
        st.markdown("**Inventory Position**")
        st.write(f"On hand Inventory: **${on_hand_stock_val:,.2f}**")
        st.write(f"In-Transit Inventory: **${in_transit_val:,.2f}**")
        st.write(f"Total Committed: **${total_committed_stock:,.2f}**")
    with l3:
        st.markdown("**Net Position**")
        st.metric("Net Worth", f"${net_worth:,.2f}")
    st.divider()

    # --- TIME HORIZON ---
    st.subheader("⏳ Time Horizon")
    start_q = pd.Timestamp(today.year, (today.month - 1) // 3 * 3 + 1, 1)
    start_y = pd.Timestamp(today.year, 1, 1)
    date_6m = today - timedelta(days=180)
    horizons = {
        "Month-to-Date": (start_of_month, today), "Quarter-to-Date": (start_q, today),
        "Last 6 Months": (date_6m, today), "Year-to-Date": (start_y, today),
        "All Time": (pd.Timestamp.min, today)
    }
    h_data = []
    for lbl, (s, e) in horizons.items():
        m = calculate_time_horizon_metrics(sales_df, s, e)
        h_data.append({"Period": lbl, "Revenue": f"${m['Revenue']:,.2f}", "Profit": f"${m['Profit']:,.2f}"})
    st.table(pd.DataFrame(h_data))

    # --- LIFETIME TOTALS ---
    st.subheader("∞ Lifetime Totals")
    completed = sales_df[sales_df['Status'] == 'Completed'] if not sales_df.empty else pd.DataFrame()
    rev, prof = (completed['Sale_Price'].sum(), completed['Profit'].sum()) if not completed.empty else (0,0)
    sold = len(completed)
    bought = (inv_df['Quantity'].sum() if not inv_df.empty else 0) + sold
    
    t1, t2, t3, t4 = st.columns(4)
    t1.metric("Total Revenue", f"${rev:,.2f}")
    t2.metric("Total Cost", f"${rev-prof:,.2f}")
    t3.metric("Total Profit", f"${prof:,.2f}")
    t4.metric("Margin %", f"{(prof/rev*100 if rev>0 else 0):.2f}%")
    
    t5, t6, t7, t8 = st.columns(4)
    t5.metric("Pieces Bought", f"{int(bought)}")
    t6.metric("Pieces Sold", f"{sold}")
    t7.metric("WAC", f"${((rev-prof)/sold if sold>0 else 0):.2f}")
    t8.metric("Avg Rev/Pc", f"${(rev/sold if sold>0 else 0):.2f}")

# ==============================================================================
# 2. INVENTORY
# ==============================================================================
elif main_menu == "Inventory":
    st.title("📦 Inventory Overview")
    data = db.load_csv(md.INVENTORY_FILE)
    if not data: st.warning("Empty."); st.stop()

    df = pd.DataFrame(data)
    df = df[df['Color'].astype(str).str.strip() != '']
    df['Quantity'] = pd.to_numeric(df['Quantity'])
    df['WAC_Cost'] = pd.to_numeric(df['WAC_Cost'])
    df['Total Value'] = df['Quantity'] * df['WAC_Cost']
    
    st.subheader("📊 Cost Basis Summary")
    wac_summ = df.groupby(['WAC_Group', 'Brand', 'Type']).agg(
        Total_Units=('Quantity', 'sum'), Total_Cost=('Total Value', 'sum')
    ).reset_index()
    wac_summ['Avg Cost'] = wac_summ['Total_Cost'] / wac_summ['Total_Units']
    st.dataframe(wac_summ.style.format({'Total_Cost': "${:,.2f}", 'Avg Cost': "${:.2f}"}), use_container_width=True)
    
    st.divider()
    
    st.subheader("🔍 Item Explorer")
    df['Color_Rank'] = df['Color'].apply(get_custom_color_index)
    df['Type_Rank'] = df['Type'].apply(get_type_index)
    df['Size_Rank'] = df['Size'].apply(lambda x: md.SIZE_SORT_ORDER.get(x, 99))
    df['Display_Group'] = df.apply(lambda x: get_inventory_display_group(x['Brand'], x['Type']), axis=1)
    
    groups = sorted(df['Display_Group'].unique(), key=get_group_sort_order)
    for g in groups:
        gdf = df[df['Display_Group'] == g]
        qty = gdf['Quantity'].sum()
        if qty > 0:
            with st.expander(f"{g} ({qty} units)", expanded=True):
                gdf_sorted = gdf.sort_values(by=['Color_Rank', 'Type_Rank', 'Size_Rank'])
                st.dataframe(gdf_sorted[['Color', 'Type', 'Size', 'Quantity', 'WAC_Cost']].style.format({'WAC_Cost': "${:.2f}"}), use_container_width=True, hide_index=True)

# ==============================================================================
# 3. RECEIVE STOCK
# ==============================================================================
elif main_menu == "Receive Stock":
    st.title("📥 Receive Stock")
    with st.container():
        st.subheader("1. Add Items")
        c1, c2 = st.columns(2)
        with c1:
            brand = st.selectbox("Brand", list(md.SIZE_MAP.keys()) + ["Other"])
            if brand == "Other": brand = st.text_input("Brand").upper()
            type_ = st.selectbox("Type", md.BRAND_TYPES.get(brand, ["HOODIE", "PANT"]) + ["Other"])
            if type_ == "Other": type_ = st.text_input("Type").upper()
        with c2:
            color = st.selectbox("Color", md.BRAND_COLORS.get(brand, ["BLACK"]) + ["Other"])
            if color == "Other": color = st.text_input("Color").upper()
            size = st.selectbox("Size", md.SIZE_MAP.get(brand, ["S", "M"]) + ["Other"])
            if size == "Other": size = st.text_input("Size").upper()
            
        c3, c4, c5 = st.columns(3)
        qty = c3.number_input("Qty", min_value=1)
        unit_cost = c4.number_input("Cost ($)", min_value=0.01)
        
        inv = db.load_csv(md.INVENTORY_FILE)
        wac_group = md.find_wac_group(brand, type_)
        if wac_group == "UNKNOWN": wac_group = f"{brand}_{type_}"
        if inv:
            idf = pd.DataFrame(inv)
            grp_rows = idf[idf['WAC_Group'] == wac_group]
            if not grp_rows.empty:
                curr = pd.to_numeric(grp_rows['WAC_Cost']).mean()
                if unit_cost > curr * 1.1: c4.warning(f"⚠️ High! Avg: ${curr:.2f}")

        if c5.button("➕ Add"):
            st.session_state.receive_cart.append({
                "Brand": brand, "Type": type_, "Color": color, "Size": size,
                "Quantity": qty, "Unit_Cost": unit_cost, "Total_Value": qty*unit_cost, "WAC_Group": wac_group
            })
            st.success("Added")

    if st.session_state.receive_cart:
        st.subheader("2. Confirm Batch")
        batch_df = pd.DataFrame(st.session_state.receive_cart)
        edited = st.data_editor(batch_df, num_rows="dynamic", use_container_width=True, key="rec_edit")
        st.session_state.receive_cart = edited.to_dict('records')
        
        if not edited.empty:
            total = pd.to_numeric(edited['Total_Value']).sum()
            st.metric("Total Batch Cost", f"${total:,.2f}")
            if st.button("✅ COMMIT"):
                inv = db.load_csv(md.INVENTORY_FILE)
                for item in st.session_state.receive_cart:
                    found = False
                    for row in inv:
                        if (row['Brand'] == item['Brand'] and row['Type'] == item['Type'] and 
                            row['Color'] == item['Color'] and row['Size'] == item['Size']):
                            old_q, old_c = int(row['Quantity']), float(row['WAC_Cost'])
                            new_q = old_q + item['Quantity']
                            new_c = ((old_q * old_c) + (item['Quantity'] * item['Unit_Cost'])) / new_q
                            row['Quantity'] = str(new_q); row['WAC_Cost'] = str(round(new_c, 2))
                            found = True; break
                    if not found:
                        inv.append({
                            "Brand": item['Brand'], "Type": item['Type'], "Color": item['Color'], 
                            "Size": item['Size'], "Quantity": str(item['Quantity']), 
                            "WAC_Cost": str(item['Unit_Cost']), "WAC_Group": item['WAC_Group']
                        })
                db.save_csv(md.INVENTORY_FILE, md.INVENTORY_COLUMNS, inv)
                for g in set(x['WAC_Group'] for x in st.session_state.receive_cart): db.recalculate_global_wac(g)
                st.session_state.receive_cart = []; st.success("Done!"); st.rerun()
            
        if st.button("Clear Batch"): st.session_state.receive_cart = []; st.rerun()

# ==============================================================================
# 4. LOG SALE
# ==============================================================================
elif main_menu == "Log Sale":
    st.title("💰 Log Sale")
    tab_sale, tab_manage = st.tabs(["New Sale", "Manager Actions (Edit Sales)"])
    
    with tab_sale:
        inv = db.load_csv(md.INVENTORY_FILE)
        if not inv: st.error("Empty Inv"); st.stop()
        df = pd.DataFrame(inv)
        df = df[pd.to_numeric(df['Quantity']) > 0]
        
        c1, c2, c3, c4 = st.columns(4)
        brand = c1.selectbox("Brand", df['Brand'].unique())
        type_ = c2.selectbox("Type", df[df['Brand']==brand]['Type'].unique())
        color = c3.selectbox("Color", df[(df['Brand']==brand) & (df['Type']==type_)]['Color'].unique())
        
        df_c = df[(df['Brand']==brand) & (df['Type']==type_) & (df['Color']==color)]
        df_c['lbl'] = df_c['Size'] + " (" + df_c['Quantity'].astype(str) + ")"
        size_lbl = c4.selectbox("Size", df_c['lbl'].unique())
        
        if size_lbl:
            row = df_c[df_c['lbl'] == size_lbl].iloc[0]
            curr, cost = int(row['Quantity']), float(row['WAC_Cost'])
            c_q, c_p, c_a = st.columns([1, 1, 1])
            q = c_q.number_input("Qty", 1, curr, 1)
            p = c_p.number_input("Price", 0.0, value=cost*1.2)
            if c_a.button("➕ Add"):
                st.session_state.sales_cart.append({
                    "Brand": row['Brand'], "Type": row['Type'], "Color": row['Color'], "Size": row['Size'],
                    "Quantity": q, "Unit_Price": p, "Total": p*q, "Cost": cost, "WAC_Group": row.get('WAC_Group', 'UNKNOWN')
                })
                st.success("Added")

        st.divider()
        if st.session_state.sales_cart:
            cart = pd.DataFrame(st.session_state.sales_cart)
            edited = st.data_editor(cart, num_rows="dynamic", use_container_width=True, key="sale_edit")
            st.session_state.sales_cart = edited.to_dict('records')
            
            tot = edited['Total'].sum() if not edited.empty else 0
            c_stat, c_btn = st.columns(2)
            stat = c_stat.selectbox("Status", ["Completed", "Pending / Reserved"])
            
            if c_btn.button("✅ CONFIRM SALE", type="primary"):
                cinv = db.load_csv(md.INVENTORY_FILE); csales = db.load_csv(md.SALES_FILE)
                for item in st.session_state.sales_cart:
                    for r in cinv:
                        if r['Brand']==item['Brand'] and r['Color']==item['Color'] and r['Size']==item['Size'] and r['Type']==item['Type']:
                            r['Quantity'] = str(int(r['Quantity']) - item['Quantity']); break
                    prof = item['Total'] - (item['Quantity']*item['Cost'])
                    csales.append({
                        "ID": db.get_next_sale_id(), "Date": date.today().strftime("%m/%d/%Y"),
                        "Brand": item['Brand'], "Type": item['Type'], "Color": item['Color'], "Size": item['Size'],
                        "Sale_Price": str(item['Total']), "Profit": str(round(prof, 2)), "WAC_Group": item['WAC_Group'], "Status": stat
                    })
                db.save_csv(md.INVENTORY_FILE, md.INVENTORY_COLUMNS, cinv)
                db.save_csv(md.SALES_FILE, md.SALES_COLUMNS, csales)
                if stat == "Completed": db.update_cash_on_hand(tot)
                st.session_state.sales_cart = []; st.success("Sold!"); st.rerun()
            if st.button("Clear"): st.session_state.sales_cart = []; st.rerun()

    with tab_manage:
        st.subheader("Edit Past Sales")
        sid = st.text_input("Enter Sale ID")
        if sid:
            sales = db.load_csv(md.SALES_FILE)
            target = next((s for s in sales if s['ID'] == sid), None)
            if target:
                st.write(f"Editing: {target['Brand']} {target['Type']} - ${target['Sale_Price']}")
                with st.form("edit_s"):
                    np = st.number_input("Correct Price", value=float(target['Sale_Price']))
                    nd = st.text_input("Date", value=target['Date'])
                    if st.form_submit_button("Update"):
                        diff = np - float(target['Sale_Price'])
                        db.update_cash_on_hand(diff)
                        target['Sale_Price'] = str(np); target['Date'] = nd
                        cost_est = float(target['Sale_Price']) - float(target['Profit'])
                        target['Profit'] = str(np - cost_est)
                        db.save_csv(md.SALES_FILE, md.SALES_COLUMNS, sales)
                        st.success("Updated")

# ==============================================================================
# 5. PURCHASING (MANAGE ORDERS)
# ==============================================================================
elif main_menu == "Purchasing":
    tab1, tab2, tab3 = st.tabs(["Create Order", "Receive Stock", "Manage Orders"])
    
    with tab1: # Create
        st.header("📝 Create Purchase Order")
        c1, c2 = st.columns(2)
        supplier = c1.text_input("Supplier")
        order_date = c2.date_input("Date", value=date.today())
        
        c3, c4, c5, c6 = st.columns(4)
        brand = c3.selectbox("Brand PO", list(md.SIZE_MAP.keys()) + ["Other"])
        type_ = c4.selectbox("Type PO", ["HOODIE", "PANT", "TEE", "SHORTS"] + ["Other"])
        qty = c5.number_input("Qty PO", 1)
        cost = c6.number_input("Total Cost PO", 0.0)
        
        wac_group = md.find_wac_group(brand, type_)
        if wac_group == "UNKNOWN": wac_group = f"{brand}_{type_}"
        inv = db.load_csv(md.INVENTORY_FILE)
        if inv:
            idf = pd.DataFrame(inv)
            grp = idf[idf['WAC_Group'] == wac_group]
            if not grp.empty:
                curr = pd.to_numeric(grp['WAC_Cost']).mean()
                if (cost/qty if qty>0 else 0) > curr * 1.1: c6.warning(f"High! Avg: ${curr:.2f}")

        if st.button("Add Line"):
            st.session_state.purchase_cart.append({
                "WAC_Group": wac_group, "Total_Pieces": qty, "Total_Cost": cost, "Unit_Cost": cost/qty
            })
            
        if st.session_state.purchase_cart:
            pdf = pd.DataFrame(st.session_state.purchase_cart)
            edited = st.data_editor(pdf, num_rows="dynamic", key="po_edit")
            st.session_state.purchase_cart = edited.to_dict('records')
            
            g_total = pd.to_numeric(edited['Total_Cost']).sum() if not edited.empty else 0
            st.metric("Order Total", f"${g_total:,.2f}")
            
            if st.button("💾 SAVE ORDER", type="primary"):
                new_id = db.get_next_order_id()
                orders = db.load_csv(md.ORDERS_FILE)
                for i in st.session_state.purchase_cart:
                    orders.append({
                        "Order_ID": new_id, "Date": order_date.strftime("%m/%d/%Y"),
                        "WAC_Group": i['WAC_Group'], "Supplier": supplier, 
                        "Total_Pieces": str(i['Total_Pieces']), "Total_Cost": str(i['Total_Cost']),
                        "Unit_Cost": str(i['Unit_Cost']), "Amount_Paid": "0", "Payment_Status": "Unpaid", 
                        "Status": "Ordered", "Delivery_Date": "N/A"
                    })
                db.save_csv(md.ORDERS_FILE, md.ORDER_COLUMNS, orders)
                st.session_state.purchase_cart = []; st.success(f"Order #{new_id} Saved"); st.rerun()

    with tab2: st.info("Use 'Manage Orders' to verify receipts.")

    with tab3: # MANAGE
        st.header("Manage Existing Orders")
        orders = db.load_csv(md.ORDERS_FILE)
        if not orders: st.info("No Orders"); st.stop()
        
        odf = pd.DataFrame(orders)
        if 'Delivery_Date' not in odf.columns: odf['Delivery_Date'] = "N/A"
        sel_oid = st.selectbox("Select Order ID", odf['Order_ID'].unique())
        
        target_rows = [o for o in orders if o['Order_ID'] == sel_oid]
        
        display_data = []
        for r in target_rows:
            rem = float(r['Total_Cost']) - float(r['Amount_Paid'])
            display_data.append({
                "WAC Group": r['WAC_Group'], "Pieces": r['Total_Pieces'], 
                "Cost": float(r['Total_Cost']), "Remaining": rem, "Paid": float(r['Amount_Paid']),
                "Status": r['Status'], "Delivery": r.get('Delivery_Date', 'N/A')
            })
        
        st.write("### Order Lines (Edit or Delete Lines)")
        edited_order = st.data_editor(pd.DataFrame(display_data), num_rows="dynamic", key="manage_edit")
        
        if st.button("💾 Save Line Changes"):
            new_master_list = [o for o in orders if o['Order_ID'] != sel_oid]
            for _, row in edited_order.iterrows():
                orig = next((x for x in target_rows if x['WAC_Group'] == row['WAC Group']), target_rows[0])
                new_line = {
                    "Order_ID": sel_oid, "Date": orig['Date'], "Supplier": orig['Supplier'],
                    "WAC_Group": row['WAC Group'], "Total_Pieces": str(row['Pieces']),
                    "Total_Cost": str(row['Cost']), "Unit_Cost": str(row['Cost']/row['Pieces'] if row['Pieces']>0 else 0),
                    "Amount_Paid": str(row['Paid']), 
                    "Payment_Status": 'Paid' if row['Paid'] >= row['Cost'] else 'Partial',
                    "Status": row['Status'], "Delivery_Date": row['Delivery']
                }
                new_master_list.append(new_line)
            db.save_csv(md.ORDERS_FILE, md.ORDER_COLUMNS, new_master_list)
            st.success("Order Updated!"); st.rerun()

        st.divider()
        
        c_pay, c_del = st.columns(2)
        with c_pay:
            st.subheader("Update Payment")
            curr_paid = sum(float(r['Amount_Paid']) for r in target_rows)
            tot_cost = sum(float(r['Total_Cost']) for r in target_rows)
            
            new_paid_total = st.number_input("Total Amount Paid", value=curr_paid)
            
            if st.button("Update Payment"):
                diff = new_paid_total - curr_paid
                if diff != 0: db.update_cash_on_hand(-diff)
                
                fresh_orders = db.load_csv(md.ORDERS_FILE)
                for r in fresh_orders:
                    if r['Order_ID'] == sel_oid:
                        share = float(r['Total_Cost']) / tot_cost if tot_cost > 0 else 0
                        r['Amount_Paid'] = str(round(new_paid_total * share, 2))
                        r['Payment_Status'] = 'Paid' if float(r['Amount_Paid']) >= float(r['Total_Cost']) else 'Partial'
                db.save_csv(md.ORDERS_FILE, md.ORDER_COLUMNS, fresh_orders)
                st.success("Payment Distributed & Cash Updated"); st.rerun()

        with c_del:
            st.subheader("Delete Order")
            if st.button("DELETE ENTIRE ORDER", type="primary"):
                if curr_paid > 0:
                    db.update_cash_on_hand(curr_paid)
                    st.warning(f"Refunded ${curr_paid} to cash.")
                final_list = [o for o in orders if o['Order_ID'] != sel_oid]
                db.save_csv(md.ORDERS_FILE, md.ORDER_COLUMNS, final_list)
                st.success("Deleted"); st.rerun()

# ==============================================================================
# 6. ANALYTICS & TOOLS
# ==============================================================================
elif main_menu == "Analytics":
    st.title("📈 Performance")
    sales_data = db.load_csv(md.SALES_FILE)
    if sales_data:
        sdf = pd.DataFrame(sales_data)
        sdf['Profit'] = pd.to_numeric(sdf['Profit'])
        sdf['Sale_Price'] = pd.to_numeric(sdf['Sale_Price'])
        if 'Status' in sdf.columns: sdf = sdf[sdf['Status'] == 'Completed']
        st.subheader("Brand Performance")
        bstats = sdf.groupby('Brand')[['Sale_Price', 'Profit']].sum().reset_index()
        bstats['Margin %'] = (bstats['Profit'] / bstats['Sale_Price']) * 100
        st.dataframe(bstats.style.format({'Sale_Price': "${:,.2f}", 'Profit': "${:,.2f}", 'Margin %': "{:.2f}%"}))

elif main_menu == "Admin Tools":
    st.title("🛠️ Admin Tools")
    if st.button("Clean Inventory"):
        inv = db.load_csv(md.INVENTORY_FILE)
        cln = [r for r in inv if r.get('Color') and str(r['Color']).strip() != ""]
        db.save_csv(md.INVENTORY_FILE, md.INVENTORY_COLUMNS, cln)
        st.success("Done")