# 🏔️ Everest AI - 7Span Intelligent Assistant

A full-stack ChatGPT-style conversational assistant built with Streamlit and Python for **7Span Everest**.

---

## 🚀 Quick Start (1-Click Run)

### Method 1: Double-click `run.bat`
Simply double-click the `run.bat` file in this folder. It will launch the application and open your browser automatically.

### Method 2: From Terminal
```powershell
cd D:\Everest-AI
streamlit run app.py
```
Open **`http://localhost:8501`** in your browser!

---

## 📁 Project Structure

```
D:\Everest-AI\
├── app.py                 # Streamlit ChatGPT-style UI (Charts, Tables, Metric cards)
├── database.py            # SQLite & MySQL Database Manager
├── query_engine.py        # Natural Language to SQL Query Engine
├── everest_dummy.db       # Local SQLite Database (Pre-loaded with 7Span data)
├── requirements.txt       # Python dependencies
├── run.bat                # 1-Click Windows Launcher
└── README.md              # Project Documentation
```

---

## 🔌 Connecting to Live Everest MySQL Database

By default, the application runs on the local `everest_dummy.db` database.

When you are ready to connect to your **live Everest MySQL database**:
1. Open `database.py`.
2. Edit the `MYSQL_CONFIG` block:
   ```python
   MYSQL_CONFIG = {
       "enabled": True,  # Change to True!
       "host": "your_db_host",
       "port": 3306,
       "user": "your_read_only_user",
       "password": "your_password",
       "database": "everest"
   }
   ```
3. Restart the app!
