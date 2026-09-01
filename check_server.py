import requests
import time

print('Checking if server is running...')
time.sleep(1)

try:
    resp = requests.get('http://localhost:8000/api/health', timeout=5)
    if resp.status_code == 200:
        print()
        print('=' * 60)
        print('SERVER IS RUNNING!')
        print('=' * 60)
        print()
        print('Access your app at:')
        print('  http://localhost:8000')
        print('  http://localhost:8000/auth.html')
        print('  http://localhost:8000/portfolio.html')
        print('  http://localhost:8000/analysis.html')
        print('=' * 60)
    else:
        print(f'Server returned: {resp.status_code}')
except Exception as e:
    print(f'Server not ready yet: {e}')
    print('Please wait a few more seconds and try again')
