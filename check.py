import subprocess
import time
import sys

print("Checking server status...")
import requests
try:
    r = requests.get('http://localhost:8000/api/health', timeout=3)
    if r.status_code == 200:
        print("✓ Server is running!")
        sys.exit(0)
except:
    print("✗ Server not running. Please start it first.")
    print("Run: cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000")
    sys.exit(1)
