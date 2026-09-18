# -*- coding: utf-8 -*-
import os
import re
import sqlite3
import pandas as pd
from typing import List, Dict, Any, Union

DB_PATH = os.path.join(os.path.dirname(__file__), "everest_dummy.db")

COMMON_ENCODINGS = ["utf-8", "utf-8-sig", "latin1", "cp1252", "iso-8859-1"]

def sanitize_table_name(name: str) -> str:
    """Sanitizes filename into a clean SQL table name."""
    base = os.path.splitext(os.path.basename(name))[0]
    # Replace non-alphanumeric characters with underscores
    clean = re.sub(r'[^a-zA-Z0-9_]+', '_', base).strip('_').lower()
    if not clean or clean[0].isdigit():
        clean = "tbl_" + clean
    return clean

def sanitize_column_name(col: str) -> str:
    """Cleans column names for SQL compatibility while preserving readability."""
    cleaned = str(col).strip()
    cleaned = re.sub(r'[^\w\s-]', '', cleaned)
    cleaned = re.sub(r'[-\s]+', '_', cleaned)
    return cleaned

def read_csv_safely(file_source: Union[str, Any]) -> pd.DataFrame:
    """Reads a CSV file or buffer trying multiple encodings."""
    last_err = None
    for enc in COMMON_ENCODINGS:
        try:
            if hasattr(file_source, 'seek'):
                file_source.seek(0)
            df = pd.read_csv(file_source, encoding=enc, low_memory=False)
            return df
        except Exception as e:
            last_err = e
            continue
    raise ValueError(f"Failed to read CSV with common encodings. Last error: {last_err}")

def import_single_csv(file_source: Union[str, Any], file_name: str, db_path: str = DB_PATH) -> Dict[str, Any]:
    """
    Imports a single CSV into SQLite.
    Supports either file path (str) or file-like buffer (UploadedFile from Streamlit).
    """
    try:
        df = read_csv_safely(file_source)
        if df.empty:
            return {
                "file_name": file_name,
                "table_name": None,
                "rows": 0,
                "columns": [],
                "status": "Empty File (Skipped)"
            }

        # Sanitize column names
        df.columns = [sanitize_column_name(c) for c in df.columns]
        table_name = sanitize_table_name(file_name)

        # Write to SQLite
        conn = sqlite3.connect(db_path)
        try:
            df.to_sql(table_name, conn, if_exists="replace", index=False)
            conn.commit()
        finally:
            conn.close()

        return {
            "file_name": file_name,
            "table_name": table_name,
            "rows": len(df),
            "columns": list(df.columns),
            "status": "Success"
        }
    except Exception as e:
        return {
            "file_name": file_name,
            "table_name": None,
            "rows": 0,
            "columns": [],
            "status": f"Error: {str(e)}"
        }

def import_csv_folder(folder_path: str, db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    """Imports all CSV files found inside a folder into SQLite."""
    results = []
    if not os.path.exists(folder_path):
        return results

    csv_files = [f for f in os.listdir(folder_path) if f.lower().endswith(".csv")]
    for f in csv_files:
        full_path = os.path.join(folder_path, f)
        res = import_single_csv(full_path, f, db_path=db_path)
        results.append(res)

    return results

def get_database_catalog(db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    """Returns a list of all tables in the SQLite database with row counts and column names."""
    if not os.path.exists(db_path):
        return []

    conn = sqlite3.connect(db_path)
    catalog = []
    try:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        tables = [row[0] for row in cur.fetchall()]
        
        for tbl in tables:
            try:
                cur.execute(f"SELECT COUNT(*) FROM `{tbl}`")
                row_count = cur.fetchone()[0]
                cur.execute(f"PRAGMA table_info(`{tbl}`)")
                columns = [col[1] for col in cur.fetchall()]
                catalog.append({
                    "table_name": tbl,
                    "rows": row_count,
                    "columns": columns,
                    "column_count": len(columns)
                })
            except Exception:
                continue
    finally:
        conn.close()

    return sorted(catalog, key=lambda x: x["table_name"])
