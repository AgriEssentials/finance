"""
Diagnostic script for Supabase connection
"""
import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

print("=" * 70)
print("SUPABASE CONNECTION DIAGNOSTIC")
print("=" * 70)

# Parse project ref from URL
project_ref = ""
if SUPABASE_URL:
    # Extract from https://xxxxxxxx.supabase.co
    parts = SUPABASE_URL.replace("https://", "").split(".")
    if parts:
        project_ref = parts[0]

print(f"\n[PROJECT INFO]")
print(f"  SUPABASE_URL: {SUPABASE_URL}")
print(f"  Project Ref:  {project_ref}")

print(f"\n[DATABASE_URL]")
print(f"  {DATABASE_URL}")

# Check if project ref matches
if project_ref and project_ref in DATABASE_URL:
    print(f"  [OK] Project ref matches")
else:
    print(f"  [ERROR] Project ref MISMATCH!")
    print(f"    URL has: {project_ref}")
    print(f"    But DATABASE_URL has different project")

# Test connection with verbose output
print(f"\n[CONNECTION TEST]")
try:
    import psycopg2
    
    # Parse connection string
    # postgresql://username:password@host:port/database
    conn_str = DATABASE_URL
    
    print(f"  Attempting to connect...")
    print(f"  Host: aws-0-ap-northeast-2.pooler.supabase.com")
    print(f"  Port: 5432")
    print(f"  User: postgres.{project_ref}")
    print(f"  Password: {'*' * 10} (hidden)")
    
    conn = psycopg2.connect(conn_str)
    
    # If we get here, connection worked
    cursor = conn.cursor()
    cursor.execute("SELECT version();")
    version = cursor.fetchone()
    print(f"\n  [SUCCESS] CONNECTION SUCCESSFUL!")
    print(f"  PostgreSQL version: {version[0][:50]}...")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"\n  [FAILED] CONNECTION FAILED")
    print(f"  Error: {e}")
    
    # Provide troubleshooting steps
    print(f"\n[TROUBLESHOOTING]")
    print(f"  1. Verify your project is fully provisioned")
    print(f"     Go to: {SUPABASE_URL}")
    print(f"  2. Check if Session Pooler is enabled")
    print(f"     Dashboard → Database → Connection Pooling")
    print(f"  3. Try resetting your database password:")
    print(f"     Dashboard → Settings → Database → Reset Password")
    print(f"  4. Make sure the password doesn't have special chars that break URL")
    print(f"  5. Wait 5-10 minutes if project was just created")

print("\n" + "=" * 70)
print("DIAGNOSTIC COMPLETE")
print("=" * 70)
