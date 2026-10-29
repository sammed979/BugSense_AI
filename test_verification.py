import requests

# Login
r = requests.post('http://localhost:8000/api/v1/auth/login/', json={'username':'testuser','password':'TestPassword123!'})
print(f"Login status: {r.status_code}")
token = r.json()['access']

# Test verification
verification_data = {
    'original_code': 'print(total_price)',
    'repaired_code': 'total_price = None\nprint(total_price)',
    'language': 'python'
}

r2 = requests.post('http://localhost:8000/api/v1/verification/', 
                   headers={'Authorization':f'Bearer {token}'}, 
                   json=verification_data)
print(f"Verification status: {r2.status_code}")
print(r2.text)
