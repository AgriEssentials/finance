import subprocess
import time
import sys

# Start server
proc = subprocess.Popen(
    [sys.executable, '-m', 'uvicorn', 'app.main:app', '--host', '0.0.0.0', '--port', '8000'],
    stdout=open('server.log', 'w'),
    stderr=subprocess.STDOUT
)

print(f'Server starting with PID: {proc.pid}')
time.sleep(8)

# Test
import requests
try:
    response = requests.get('http://localhost:8000/api/portfolio/stocks', timeout=10)
    print(f'Status: {response.status_code}')
    if response.status_code == 200:
        data = response.json()
        print(f'Got {len(data["stocks"])} stocks')
        for s in data["stocks"][:3]:
            print(f"  {s['symbol']}: ₹{s.get('current_price', 'N/A')}")
    else:
        print(f'Error: {response.text}')
except Exception as e:
    print(f'Error: {e}')
