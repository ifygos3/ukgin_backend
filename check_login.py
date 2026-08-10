import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ukgin_config.settings')
import django
django.setup()
import requests
url = 'http://127.0.0.1:8000/users/login/'
payload = {'username': 'ifygos', 'password': 'Admin123!'}
headers = {'Content-Type': 'application/json'}
resp = requests.post(url, json=payload, headers=headers)
print('Status:', resp.status_code)
try:
    print('Response:', resp.json())
except:
    print('Response text:', resp.text[:500])
