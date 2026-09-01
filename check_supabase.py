"""
Script to check Supabase auth and database in detail
"""
import os
from dotenv import load_dotenv
import requests

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY", "").strip()

print(f"SUPABASE_URL: {SUPABASE_URL}")
print(f"SUPABASE_KEY: {SUPABASE_KEY[:20]}...")
print()

if not SUPABASE_URL or not SUPABASE_KEY:
    print("ERROR: Supabase credentials not configured!")
    exit(1)

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

print("=" * 60)
print("CHECKING SUPABASE PROJECT STATUS")
print("=" * 60)

# Check health
health_url = f"{SUPABASE_URL}/rest/v1/"
try:
    response = requests.get(health_url, headers=headers, timeout=10)
    print(f"REST API Status: {response.status_code}")
    if response.status_code == 200:
        print("REST API is accessible")
    else:
        print(f"Response: {response.text[:200]}")
except Exception as e:
    print(f"REST API Error: {e}")

print()
print("=" * 60)
print("CHECKING AUTH ENDPOINT")
print("=" * 60)

# Check auth settings
auth_settings_url = f"{SUPABASE_URL}/auth/v1/settings"
try:
    response = requests.get(auth_settings_url, headers=headers, timeout=10)
    print(f"Auth Settings Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Disable Signup: {data.get('disable_signup', 'N/A')}")
        print(f"External Providers: {data.get('external_labels', [])}")
        print(f"Mailer Autoconfirm: {data.get('mailer_autoconfirm', 'N/A')}")
        print(f"Phone Autoconfirm: {data.get('phone_autoconfirm', 'N/A')}")
        print(f"SMS Provider: {data.get('sms_provider', 'N/A')}")
    else:
        print(f"Response: {response.text[:500]}")
except Exception as e:
    print(f"Auth Settings Error: {e}")

print()
print("=" * 60)
print("TESTING USER REGISTRATION (DETAILED)")
print("=" * 60)

signup_url = f"{SUPABASE_URL}/auth/v1/signup"
test_email = "test_debug_12345@test.com"
test_password = "TestPass123!"

payload = {
    "email": test_email,
    "password": test_password,
    "data": {"full_name": "Test User"}
}

try:
    response = requests.post(signup_url, headers=headers, json=payload, timeout=10)
    print(f"Signup Status: {response.status_code}")
    print(f"Response: {response.text[:500]}")

    if response.status_code == 200:
        data = response.json()
        print("SUCCESS: User created!")
        print(f"User ID: {data.get('id', 'N/A')}")
        print(f"Email: {data.get('email', 'N/A')}")
        print(f"Confirmation Sent: {data.get('confirmation_sent_at') is not None}")
    elif response.status_code == 400:
        print("FAILED: Bad request - check error message above")
    elif response.status_code == 422:
        print("FAILED: Validation error")
    else:
        print(f"FAILED: Unexpected status code {response.status_code}")
except Exception as e:
    print(f"Signup Request Error: {e}")

print()
print("=" * 60)
print("CHECKING POSSIBLE CAUSES")
print("=" * 60)

print("""
Common causes of 'Database error saving new user':

1. AUTH SCHEMA NOT INITIALIZED
   - The auth schema tables weren't created during project setup
   - Solution: Go to Supabase Dashboard -> Authentication -> Users
   - If you see 'No users yet', the auth schema exists
   - If you see an error, the auth schema is broken

2. ROW LEVEL SECURITY (RLS) POLICIES
   - RLS policies might be blocking inserts to auth.users
   - Solution: Check RLS policies in SQL Editor

3. DATABASE CONNECTION ISSUES
   - Supabase database might be paused or having issues
   - Solution: Check Supabase Dashboard status

4. PERMISSION ISSUES
   - The anon key might not have proper permissions
   - Solution: Check Project Settings -> API -> JWT Settings

RECOMMENDED FIXES:
- Go to your Supabase Dashboard: https://app.supabase.com
- Navigate to your project
- Go to "SQL Editor"
- Run: SELECT * FROM auth.users LIMIT 1;
- If this fails, your auth schema is not set up correctly

To reset auth:
1. Go to Authentication -> Settings
2. Toggle "Disable new users" off and on
3. Or recreate the auth schema by running the auth setup SQL
""")
