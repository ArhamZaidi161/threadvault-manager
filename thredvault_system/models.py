# thredvault_system/models.py
import os

# --- FILE CONFIGURATION ---
INVENTORY_FILE = 'inventory.csv'
SALES_FILE = 'sales.csv'
ORDERS_FILE = 'orders.csv'
FINANCIALS_FILE = 'financials.csv'
BACKUP_DIR = 'backups'

# --- COLUMNS (UPDATED WITH DELIVERY DATE) ---
ORDER_COLUMNS = [
    "Order_ID", "Date", "Delivery_Date", "WAC_Group", "Supplier", 
    "Total_Pieces", "Total_Cost", "Unit_Cost", 
    "Amount_Paid", "Payment_Status", "Status"
]

INVENTORY_COLUMNS = ["Brand", "Type", "Color", "Size", "Quantity", "WAC_Cost", "WAC_Group"]
SALES_COLUMNS = ["ID", "Date", "Brand", "Type", "Color", "Size", "Sale_Price", "Profit", "WAC_Group", "Status"]

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

# --- SORTING & LOGIC ---
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

BRAND_PRIORITY = ["ESSENTIALS", "DENIM TEARS", "SP5DER", "ERIC EMANUEL", "YZY"]

BRAND_COLORS = {
    "ESSENTIALS": ["B22", "L/O", "D/O", "1977 IRON", "1977 D/O", "BLACK"],
    "SP5DER": ["PINK", "BLUE", "BLACK"],
    "DENIM TEARS": ["BLACK", "GREY"],
    "ERIC EMANUEL": ["BLACK", "NAVY", "GREY", "LIGHT BLUE", "RED", "WHITE"],
    "YZY": ["ONYX", "BONE"]
}

BRAND_TYPES = {
    "ESSENTIALS": ["HOODIE", "PANT", "TEE", "SHORTS"],
    "SP5DER": ["HOODIE", "PANT"],
    "DENIM TEARS": ["HOODIE", "PANT"],
    "ERIC EMANUEL": ["SHORTS"],
    "YZY": ["SLIDES"]
}

def find_wac_group(brand, type_):
    for group, types in WAC_TO_TYPES.items():
        mapped_brand = WAC_TO_BRAND.get(group)
        if mapped_brand == str(brand).upper() and str(type_).upper() in types:
            return group
    return "UNKNOWN"