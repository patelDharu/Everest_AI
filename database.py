import os
import sqlite3
import pandas as pd

# Path to local SQLite dummy database
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SQLITE_PATH = os.path.join(BASE_DIR, "everest_dummy.db")

# Live MySQL Database Configuration (Optional - for connecting to live Everest)
MYSQL_CONFIG = {
    "enabled": False, # Set to True when you want to connect to live MySQL
    "host": "localhost",
    "port": 3306,
    "user": "everest_read_only",
    "password": "your_password_here",
    "database": "everest"
}

def get_connection():
    """Returns a connection based on the active mode (SQLite or MySQL)."""
    if MYSQL_CONFIG["enabled"]:
        import mysql.connector
        return mysql.connector.connect(
            host=MYSQL_CONFIG["host"],
            port=MYSQL_CONFIG["port"],
            user=MYSQL_CONFIG["user"],
            password=MYSQL_CONFIG["password"],
            database=MYSQL_CONFIG["database"]
        )
    else:
        if not os.path.exists(SQLITE_PATH):
            raise FileNotFoundError(f"SQLite database not found at: {SQLITE_PATH}")
        return sqlite3.connect(SQLITE_PATH)

def run_query(sql: str, params=()) -> pd.DataFrame:
    """Executes a read-only SQL query and returns a pandas DataFrame."""
    conn = get_connection()
    try:
        df = pd.read_sql_query(sql, conn, params=params)
        return df
    finally:
        conn.close()

def execute_update(sql: str, params=()) -> int:
    """Executes an UPDATE/INSERT query and returns affected rows count."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()

def get_all_employees() -> list:
    """Returns list of all employees (id, name, role, grade)."""
    df = run_query("SELECT id, name, role, grade FROM employees ORDER BY name ASC")
    return df.to_dict('records')

def get_database_status() -> dict:
    """Returns the current database status and record counts."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM projects")
        projects_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM billables")
        billables_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM timesheets")
        timesheets_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM employees")
        employees_count = cursor.fetchone()[0]
        
        return {
            "mode": "Live MySQL" if MYSQL_CONFIG["enabled"] else "Local SQLite (Dummy DB)",
            "projects": projects_count,
            "billables": billables_count,
            "timesheets": timesheets_count,
            "employees": employees_count,
            "connected": True
        }
    except Exception as e:
        return {
            "mode": "Error",
            "connected": False,
            "error": str(e)
        }
    finally:
        conn.close()
