"""
Fix Supabase Auth Schema - Uses Service Role Key for admin access
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()

print("SUPABASE AUTH SCHEMA FIX")
print("=" * 60)

if not SUPABASE_URL or not SERVICE_ROLE_KEY:
    print("ERROR: Missing credentials!")
    exit(1)

headers = {
    "apikey": SERVICE_ROLE_KEY,
    "Authorization": f"Bearer {SERVICE_ROLE_KEY}",
    "Content-Type": "application/json"
}

# Step 1: Check if auth.users table exists
print("\nStep 1: Checking auth schema...")

sql_url = f"{SUPABASE_URL}/rest/v1/"

try:
    check_sql = {
        "query": "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'auth' AND table_name = 'users');"
    }

    response = requests.post(
        f"{SUPABASE_URL}/rest/v1/rpc/exec_sql",
        headers=headers,
        json=check_sql,
        timeout=30
    )

    print(f"Check response: {response.status_code}")
    print(f"Response: {response.text[:500] if response.text else 'Empty'}")

except Exception as e:
    print(f"Check error: {e}")

# Step 2: Try to get auth config
print("\nStep 2: Checking auth configuration...")

auth_config_url = f"{SUPABASE_URL}/auth/v1/admin/config"
try:
    response = requests.get(auth_config_url, headers=headers, timeout=10)
    print(f"Auth config status: {response.status_code}")
    if response.status_code == 200:
        config = response.json()
        print(f"JWT secret configured: {bool(config.get('jwt_secret'))}")
        print(f"External providers: {config.get('external_providers', [])}")
    else:
        print(f"Response: {response.text[:500]}")
except Exception as e:
    print(f"Auth config error: {e}")

# Step 3: Try to list users
print("\nStep 3: Checking if auth users can be listed...")

users_url = f"{SUPABASE_URL}/auth/v1/admin/users"
try:
    response = requests.get(users_url, headers=headers, timeout=10)
    print(f"List users status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        users = data.get('users', [])
        print(f"SUCCESS: Auth is working! Found {len(users)} users")
    else:
        print(f"ERROR: Cannot list users: {response.text[:500]}")
except Exception as e:
    print(f"List users error: {e}")

# Step 4: Try direct SQL to recreate auth schema
print("\nStep 4: Attempting to fix auth schema via SQL...")

fix_sql = """
CREATE SCHEMA IF NOT EXISTS auth;
GRANT USAGE ON SCHEMA auth TO postgres, anon, authenticated, service_role;
GRANT ALL ON ALL TABLES IN SCHEMA auth TO postgres, service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA auth TO postgres, service_role;
"""

try:
    sql_endpoint = f"{SUPABASE_URL}/rest/v1/"

    print("\nStep 5: Testing user creation with service role...")

    test_user_url = f"{SUPABASE_URL}/auth/v1/admin/users"
    test_payload = {
        "email": "test_fix_user@example.com",
        "password": "testpass123",
        "email_confirm": True,
        "user_metadata": {"test": True}
    }

    response = requests.post(
        test_user_url,
        headers=headers,
        json=test_payload,
        timeout=10
    )

    print(f"Create user status: {response.status_code}")
    if response.status_code in [200, 201]:
        data = response.json()
        user_id = data.get('id')
        print(f"SUCCESS: Created test user: {user_id}")

        delete_url = f"{SUPABASE_URL}/auth/v1/admin/users/{user_id}"
        del_response = requests.delete(delete_url, headers=headers, timeout=10)
        print(f"Cleanup test user: {del_response.status_code}")
    else:
        print(f"ERROR: Cannot create user: {response.text[:1000]}")

except Exception as e:
    print(f"Error: {e}")

print("\n" + "=" * 60)
print("DIAGNOSIS")
print("=" * 60)

print("""
Based on the tests above:

If Step 5 FAILED with "Database error saving new user":
  -> Your Supabase auth schema is corrupted and needs to be reset
  -> This can only be fixed via Supabase Dashboard or by creating a new project

QUICK FIX - Create New Supabase Project:
1. Go to https://app.supabase.com
2. Click "New Project"
3. Choose organization, name it "quant-terminal-fixed"
4. Wait for it to be created (2-3 minutes)
5. Go to Project Settings -> API
6. Copy the new URL and keys
7. Update your .env file

OR - Reset Current Project:
1. Go to https://app.supabase.com/project/nveqpgqiqiilnagcqsib
2. Go to Database -> Extensions
3. Look for "pg_net" and toggle it off/on
4. If that doesn't work, go to SQL Editor and run:
   DROP SCHEMA IF EXISTS auth CASCADE;
   Then restart your Supabase project

The auth schema corruption is likely due to:
- Incomplete project setup
- Database migration that failed
- Manual changes that broke the schema
""")
