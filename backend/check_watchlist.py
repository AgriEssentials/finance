"""
Check watchlist table structure - try with proper UUID
"""
import uuid
from supabase import create_client

SUPABASE_URL = "https://xhvkdsryjsntqladgufk.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inhodmtkc3J5anNudHFsYWRndWZrIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3Njg0NDU0MiwiZXhwIjoyMDkyNDIwNTQyfQ.29CLLklOmpkpvt_AhRZ5VJzzV2LO25XfgYbM3my0tM4"

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# Try to insert a test record with valid UUID to see what columns exist
try:
    test_id = str(uuid.uuid4())
    test = supabase.table("watchlist").insert({
        "user_id": test_id,
        "symbol": "TEST.NS"
    }).execute()
    if test.data:
        columns = list(test.data[0].keys())
        print(f"Watchlist columns: {columns}")
        # Clean up
        supabase.table("watchlist").delete().eq("id", test.data[0]["id"]).execute()
        print("Test record cleaned up")
except Exception as e:
    print(f"Insert error: {e}")
    # Try minimal insert
    try:
        test_id = str(uuid.uuid4())
        test = supabase.table("watchlist").insert({
            "user_id": test_id,
            "symbol": "TEST.NS"
        }).execute()
    except Exception as e2:
        print(f"Full error: {e2}")
