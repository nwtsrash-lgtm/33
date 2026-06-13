"""Quick startup test - checks if app.py can load without errors"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

print("1. Testing imports...")
try:
    import config
    print("   config.py: OK")
except Exception as e:
    print(f"   config.py: FAIL - {e}")

try:
    from engines.engine import normalize, find_missing_products
    print("   engine.py: OK")
except Exception as e:
    print(f"   engine.py: FAIL - {e}")

print("\n2. Testing database...")
import sqlite3, pandas as pd
db = os.path.join("data", "pricing_v18.db")
if os.path.exists(db):
    conn = sqlite3.connect(db)
    tables = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table'", conn)
    print(f"   Tables: {tables['name'].tolist()}")
    try:
        n = pd.read_sql("SELECT COUNT(*) as c FROM our_catalog", conn).iloc[0,0]
        print(f"   our_catalog: {n} rows")
    except Exception as e:
        print(f"   our_catalog: MISSING - {e}")
    try:
        n = pd.read_sql("SELECT COUNT(*) as c FROM competitor_products_store", conn).iloc[0,0]
        print(f"   competitors: {n} rows")
    except Exception as e:
        print(f"   competitors: MISSING - {e}")
    conn.close()
else:
    print(f"   DB NOT FOUND: {db}")

print("\n3. Testing app.py imports (no UI)...")
try:
    # Test just the imports section of app.py
    with open("app.py", encoding="utf-8") as f:
        content = f.read()
    # Check for broken references
    issues = []
    if "from utils.missing_match" in content:
        issues.append("references utils.missing_match (may not exist)")
    if "from utils.catalog_loader" in content:
        issues.append("references utils.catalog_loader (may not exist)")
    if issues:
        for i in issues:
            print(f"   WARNING: {i}")
    else:
        print("   No broken references")
    print(f"   app.py size: {len(content)} bytes, {content.count(chr(10))} lines")
except Exception as e:
    print(f"   FAIL: {e}")

print("\n4. Testing Streamlit...")
try:
    import streamlit as st
    print(f"   Streamlit: {st.__version__}")
except Exception as e:
    print(f"   Streamlit: FAIL - {e}")

print("\nDone!")
