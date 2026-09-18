# -*- coding: utf-8 -*-
"""
Everest AI - Bulk CSV Ingestion Script
Usage:
    python import_csvs.py
Scans the 'data/csvs' folder and imports every CSV into the database.
"""
import os
import sys
from csv_importer import import_csv_folder, get_database_catalog

DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "csvs")
DB_PATH = os.path.join(os.path.dirname(__file__), "everest_dummy.db")

def main():
    print("=" * 60)
    print("   Everest AI - Bulk CSV Ingestion Tool")
    print("=" * 60)
    
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR, exist_ok=True)
        print(f"Created folder: {DATA_DIR}")
        print("Please copy your 30+ CSV files into this folder and run again.")
        return

    csv_files = [f for f in os.listdir(DATA_DIR) if f.lower().endswith(".csv")]
    if not csv_files:
        print(f"No CSV files found in: {DATA_DIR}")
        print("Drop your 30+ CSV files into this folder, then run this script.")
        return

    print(f"Found {len(csv_files)} CSV files. Starting ingestion into {DB_PATH}...\n")
    
    results = import_csv_folder(DATA_DIR, db_path=DB_PATH)
    
    success_count = 0
    total_rows = 0
    for r in results:
        status_symbol = "[OK]" if r["status"] == "Success" else "[ERR]"
        print(f"{status_symbol} {r['file_name']:<35} -> Table: {r['table_name']:<20} ({r['rows']} rows)")
        if r["status"] == "Success":
            success_count += 1
            total_rows += r["rows"]

    print("\n" + "=" * 60)
    print(f"Ingestion complete: {success_count}/{len(csv_files)} files loaded successfully ({total_rows:,} rows total).")
    print("=" * 60)
    
    print("\nDatabase Table Catalog:")
    catalog = get_database_catalog(DB_PATH)
    for cat in catalog:
        print(f" - {cat['table_name']}: {cat['rows']} rows ({cat['column_count']} columns)")

if __name__ == "__main__":
    main()
