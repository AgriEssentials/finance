"""
Check all table structures using Supabase system tables
"""
from supabase import create_client

SUPABASE_URL = "https://xhvkdsryjsntqladgufk.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inhodmtkc3J5anNudHFsYWRndWZrIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3Njg0NDU0MiwiZXhwIjoyMDkyNDIwNTQyfQ.29CLLklOmpkpvt_AhRZ5VJzzV2LO25XfgYbM3my0tM4"

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# Try to query information_schema to get table columns
try:
    result = supabase.table("information_schema.columns") \
        .select("table_name, column_name, data_type") \
        .eq("table_schema", "public") \
        .execute()
    
    if result.data:
        # Group by table
        tables = {}
        for row in result.data:
            table = row["table_name"]
            if table not in tables:
                tables[table] = []
            tables[table].append(f"{row['column_name']} ({row['data_type']})")
        
        # Print relevant tables
        relevant = ["profiles", "watchlist", "alerts", "users", "user_portfolios", 
                   "portfolio_positions", "portfolio_transactions"]
        for table in relevant:
            if table in tables:
                print(f"\n=== {table} ===")
                for col in tables[table]:
                    print(f"  - {col}")
    else:
        print("No schema data found")
except Exception as e:
    print(f"Error querying schema: {e}")
