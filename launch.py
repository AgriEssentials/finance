import subprocess
import time
import sys

print('=' * 60)
print('AI QUANT TERMINAL - STARTING SERVER...')
print('=' * 60)

# Start the server in background
subprocess.Popen(
    [sys.executable, '-m', 'uvicorn', 'app.main:app', '--host', '0.0.0.0', '--port', '8000', '--reload'],
    cwd='C:\\Users\\user\\Desktop\\father\\backend',
    creationflags=subprocess.CREATE_NEW_CONSOLE
)

time.sleep(3)
print()
print('Server is starting in a new window!')
print()
print('ACCESS YOUR APP:')
print('   http://localhost:8000')
print('   http://localhost:8000/auth.html')
print('   http://localhost:8000/portfolio.html')
print()
print('Wait 5-10 seconds for the server to fully start')
print('=' * 60)
