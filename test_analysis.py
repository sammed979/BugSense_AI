import requests

# Login
r = requests.post('http://localhost:8000/api/v1/auth/login/', json={'username':'testuser','password':'TestPassword123!'})
print(f"Login status: {r.status_code}")
token = r.json()['access']

# Test analysis
analysis_data = {
    'source_code': 'print(total_price)',
    'error_message': 'NameError: name total_price is not defined',
    'terminal_logs': '''Traceback (most recent call last):
  File "<string>", line 1, in <module>
NameError: name total_price is not defined''',
    'language': 'python'
}

r2 = requests.post('http://localhost:8000/api/v1/analysis/analyze/', 
                   headers={'Authorization':f'Bearer {token}'}, 
                   json=analysis_data)
print(f"Analysis status: {r2.status_code}")
print(r2.text)
