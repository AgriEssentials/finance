"""
Check Supabase tables and their structures
"""
import os
from supabase import create_client

SUPABASE_URL = "https://xhvkdsryjsntqladgufk.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inhodmtkc3J5anNudHFsYWRndWZrIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3Njg0NDU0MiwiZXhwIjoyMDkyNDIwNTQyfQ.29CLLklOmpkpvt_AhRZ5VJzzV2LO25XfgYbM3my0tM4"

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

tables_to_check = [
    'profiles',
    'user_portfolios', 
    'portfolio_positions',
    'portfolio_transactions',
    'watchlists',
    'watchlist',
    'alerts',
    'sentiment_cache',
    'users'
]

print("=" * 60)
print("SUPABASE TABLE AVAILABILITY CHECK")
print("=" * 60)

for table in tables_to_check:
    try:
        result = supabase.table(table).select('*').limit(1).execute()
        if result.data:
            columns = list(result.data[0].keys())
            print(f"\n[OK] {table}: EXISTS")
            print(f"   Columns: {', '.join(columns)}")
        else:
            print(f"\n[OK] {table}: EXISTS (empty table)")
            # Try to get columns by inserting and rolling back... or just describe
    except Exception as e:
        error_msg = str(e)
        if "does not exist" in error_msg.lower() or "404" in error_msg:
            print(f"\n[MISSING] {table}: MISSING - Table does not exist")
        elif "column" in error_msg.lower():
            print(f"\n[WARN] {table}: EXISTS but columns error: {error_msg[:80]}")
        else:
            print(f"\n[ERROR] {table}: ERROR - {error_msg[:100]}")

print("\n" + "=" * 60)
