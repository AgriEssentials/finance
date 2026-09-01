"""
Supabase Database Setup Script
Creates all required tables for the AI Stock Analysis Assistant
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print("ERROR: Supabase credentials not found in .env file!")
    print("Please ensure SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are set.")
    sys.exit(1)

print(f"Connecting to Supabase: {SUPABASE_URL}")
print(f"Service Key: {SUPABASE_SERVICE_KEY[:20]}...")

try:
    from supabase import create_client
    
    # Create client with SERVICE ROLE key (needed for admin operations)
    client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    print("✓ Connected to Supabase with service role")
    
    # Read SQL file
    sql_file_path = os.path.join(os.path.dirname(__file__), 'supabase_setup.sql')
    with open(sql_file_path, 'r') as f:
        sql_content = f.read()
    
    # Split SQL into individual statements (simple split by semicolon)
    statements = [s.strip() for s in sql_content.split(';') if s.strip()]
    
    print(f"\nExecuting {len(statements)} SQL statements...")
    print("=" * 60)
    
    # Execute each statement
    success_count = 0
    error_count = 0
    errors = []
    
    for i, statement in enumerate(statements, 1):
        # Skip comments-only statements
        clean_stmt = '\n'.join(line for line in statement.split('\n') if not line.strip().startswith('--'))
        if not clean_stmt.strip():
            continue
            
        try:
            # Use Supabase's rpc (remote procedure call) or query execution
            # Note: Supabase Python client doesn't have direct SQL execution,
            # so we'll use the REST API directly
            import requests
            
            headers = {
                "apikey": SUPABASE_SERVICE_KEY,
                "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "tx=commit"
            }
            
            # Use the pgql endpoint for SQL execution
            query_url = f"{SUPABASE_URL}/rest/v1/"
            
            # Try to execute via PostgREST
            result = requests.post(
                f"{SUPABASE_URL}/rest/v1/rpc/exec_sql",
                headers=headers,
                json={"query": statement + ";"},
                timeout=30
            )
            
            if result.status_code in [200, 201, 204]:
                success_count += 1
                print(f"✓ Statement {i}: Success")
            elif "exec_sql" in result.text and "404" in str(result.status_code):
                # RPC function doesn't exist, we need to create it first
                print(f"⚠ Statement {i}: RPC function not found. Tables will need manual creation.")
                error_count += 1
                errors.append((i, "RPC function exec_sql not found. Please run SQL manually in Supabase SQL Editor."))
                break  # Stop trying, user needs manual setup
            else:
                error_count += 1
                error_msg = result.text[:100] if result.text else f"HTTP {result.status_code}"
                errors.append((i, error_msg))
                print(f"✗ Statement {i}: {error_msg}")
                
        except Exception as e:
            error_count += 1
            errors.append((i, str(e)))
            print(f"✗ Statement {i}: {str(e)[:100]}")
    
    print("=" * 60)
    print(f"\nResults: {success_count} succeeded, {error_count} failed")
    
    if error_count > 0:
        print("\nErrors encountered:")
        for stmt_num, error in errors:
            print(f"  Statement {stmt_num}: {error}")
        
        print("\n" + "=" * 60)
        print("MANUAL SETUP REQUIRED")
        print("=" * 60)
        print("""
The automatic setup couldn't complete. Please follow these manual steps:

1. Go to your Supabase Dashboard:
   https://app.supabase.com/project/nveqpgqiqiilnagcqsib

2. Click "SQL Editor" in the left sidebar

3. Click "New Query"

4. Copy and paste the ENTIRE contents of the file:
   C:/Users/user/Desktop/father/supabase_setup.sql

5. Click "Run" to execute all statements

6. Verify the tables were created by running:
   SELECT table_name FROM information_schema.tables 
   WHERE table_schema = 'public';

This will create all required tables with proper RLS policies.
""")
        sys.exit(1)
    else:
        print("\n✓ All tables created successfully!")
        
        # Verify tables exist
        print("\nVerifying tables...")
        try:
            tables = ['profiles', 'portfolio', 'trade_history', 'watchlist', 'alerts']
            for table in tables:
                response = client.table(table).select("*", count="exact").limit(1).execute()
                count = response.count if hasattr(response, 'count') else '?'
                print(f"  ✓ {table}: accessible (rows: {count})")
        except Exception as e:
            print(f"  ⚠ Could not verify tables: {e}")
        
        print("\n" + "=" * 60)
        print("SETUP COMPLETE!")
        print("=" * 60)
        print("""
Your Supabase database is now configured with:

  ✓ profiles      - User profiles for personalized trading
  ✓ portfolio     - Stock position tracking
  ✓ trade_history - Trade journal entries
  ✓ watchlist     - User watchlists
  ✓ alerts        - Price and indicator alerts

Next steps:
1. Restart your application
2. Test user registration
3. Try the personalized trading features
""")
        
except ImportError:
    print("ERROR: supabase Python package not installed!")
    print("Run: pip install supabase")
    sys.exit(1)
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
