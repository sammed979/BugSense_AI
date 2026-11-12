import requests

# Login
r = requests.post('http://localhost:8000/api/v1/auth/login/', json={'username':'testuser','password':'TestPassword123!'})
print(f"Login status: {r.status_code}")
token = r.json()['access']

# Test repair
repair_data = {
    'source_code': 'print(total_price)',
    'error_message': 'NameError: name total_price is not defined',
    'diagnosis': {
        'error_category': 'NameError',
        'summary': 'Variable total_price is used but not defined'
    },
    'language': 'python'
}

r2 = requests.post('http://localhost:8000/api/v1/repair/', 
                   headers={'Authorization':f'Bearer {token}'}, 
                   json=repair_data)
print(f"Repair status: {r2.status_code}")
print(r2.text)
