import subprocess
import time
import sys
import os
import requests

# Kill any existing Python processes
print("Cleaning up old processes...")
subprocess.run(['taskkill', '/F', '/IM', 'python.exe'], capture_output=True)
time.sleep(2)

# Clear old log
if os.path.exists('server.log'):
    os.remove('server.log')

# Start the server
print('=' * 60)
print('🚀 STARTING AI QUANT TERMINAL SERVER')
print('=' * 60)

proc = subprocess.Popen(
    [sys.executable, '-m', 'uvicorn', 'app.main:app', '--host', '0.0.0.0', '--port', '8000'],
    stdout=open('server.log', 'w'),
    stderr=subprocess.STDOUT,
    cwd='C:\\Users\\user\\Desktop\\father\\backend'
)

print(f'Server starting with PID: {proc.pid}')
print('Waiting for server to initialize...')

# Wait for server to start
time.sleep(8)

# Check if server is running
try:
    resp = requests.get('http://localhost:8000/api/health', timeout=10)
    if resp.status_code == 200:
        print()
        print('✅ SERVER IS RUNNING!')
        print()
        print('🔗 ACCESS YOUR APP AT:')
        print('   📊 Main:     http://localhost:8000')
        print('   🔐 Login:    http://localhost:8000/auth.html')
        print('   💼 Portfolio: http://localhost:8000/portfolio.html')
        print('   📈 Analysis: http://localhost:8000/analysis.html')
        print()
        print('Press Ctrl+C in this window to stop the server')
        print('=' * 60)
    else:
        print(f'⚠️  Server returned status {resp.status_code}')
except Exception as e:
    print(f'⚠️  Server may still be starting: {e}')
    print('Check server.log for details')

# Keep running
proc.wait()
