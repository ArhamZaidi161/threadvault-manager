# utils.py
import os
import shutil
from datetime import datetime, date

def clean_text(text):
    if not text: return ""
    return text.strip().upper()

def safe_float(value):
    if not value or value.strip() == "": return 0.0
    try: return float(value)
    except ValueError: return 0.0

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

def print_aligned(label, value):
    print(f"{label:<20} {value}")

def print_header(text):
    print("\n" + "="*85)
    print(f" {text}")
    print("="*85)