"""
Check existing tables in Supabase - ASCII version for Windows
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print("ERROR: Supabase credentials not found!")
    exit(1)

headers = {
    "apikey": SUPABASE_SERVICE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    "Content-Type": "application/json"
}

print("=" * 70)
print("SUPABASE DATABASE INVENTORY")
print(f"Project: {SUPABASE_URL}")
print("=" * 70)

# Method 1: Try to query via REST API using the Supabase client
print("\n[1] Querying public schema tables via Supabase REST API...")
print("-" * 70)

try:
    from supabase import create_client
    client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    
    # Try to list tables by attempting to query them
    expected_tables = [
        "profiles", "portfolio", "trade_history", "watchlist", "alerts"
    ]
    
    existing_tables = []
    missing_tables = []
    
    for table in expected_tables:
        try:
            response = client.table(table).select("*", count="exact").limit(0).execute()
            # If we get here without error, table exists
            existing_tables.append(table)
            print(f"  [OK] {table} - EXISTS")
        except Exception as e:
            error_msg = str(e)
            if "Could not find the table" in error_msg or "PGRST205" in error_msg:
                missing_tables.append(table)
                print(f"  [MISSING] {table} - NOT FOUND")
            elif "does not exist" in error_msg.lower():
                missing_tables.append(table)
                print(f"  [MISSING] {table} - NOT FOUND")
            else:
                print(f"  [?] {table} - ERROR: {error_msg[:50]}")
    
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"\nExisting tables ({len(existing_tables)}):")
    if existing_tables:
        for t in existing_tables:
            print(f"    - {t}")
    else:
        print("    (none)")
    
    print(f"\nMissing tables ({len(missing_tables)}):")
    if missing_tables:
        for t in missing_tables:
            print(f"    - {t}")
    else:
        print("    (none)")
    
    # Check auth tables via direct API
    print("\n" + "=" * 70)
    print("[2] Checking auth schema...")
    print("-" * 70)
    
    auth_url = f"{SUPABASE_URL}/auth/v1/admin/users"
    auth_headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"
    }
    
    try:
        resp = requests.get(auth_url, headers=auth_headers, timeout=10)
        if resp.status_code == 200:
            users = resp.json()
            print(f"  [OK] auth.users table is accessible")
            print(f"       Total users in auth.users: {len(users.get('users', []))}")
        elif resp.status_code == 401:
            print(f"  [WARN] Cannot access auth.users (unauthorized)")
        else:
            print(f"  [WARN] Auth check status: {resp.status_code}")
    except Exception as e:
        print(f"  [ERROR] Auth check failed: {e}")
    
    # Provide recommendations
    print("\n" + "=" * 70)
    print("RECOMMENDATIONS")
    print("=" * 70)
    
    required_tables = ["profiles", "portfolio", "trade_history", "watchlist", "alerts"]
    missing_required = [t for t in required_tables if t in missing_tables]
    
    if missing_required:
        print(f"\n[!] You need to create {len(missing_required)} tables for personalized trading:")
        for t in missing_required:
            print(f"      - {t}")
        print("\n[>] Run this SQL in your Supabase SQL Editor:")
        print(f"    {SUPABASE_URL.replace('.co', '')}/sql-editor")
        print("\n    File: supabase_setup.sql (already created for you)")
    else:
        print("\n[SUCCESS] All required tables exist!")
    
    # Additional system info
    print("\n" + "=" * 70)
    print("ADDITIONAL INFO")
    print("=" * 70)
    
    print("\nYour application uses TWO database systems:")
    print("  1. SQLAlchemy (SQLite) - Core features:")
    print("       - users, watchlists, alerts, portfolios, paper_trades")
    print("       - strategies, backtest_results, audit_logs")
    print("\n  2. Supabase - Personalized trading features:")
    print("       - profiles - User risk tolerance, capital, strategy")
    print("       - portfolio - Live position tracking with PnL")
    print("       - trade_history - Trade journal for AI coach")
    print("       - watchlist - Real-time watchlist with alerts")
    print("       - alerts - Price and indicator alerts")
    
except ImportError:
    print("ERROR: supabase package not installed")
    print("Run: pip install supabase")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
