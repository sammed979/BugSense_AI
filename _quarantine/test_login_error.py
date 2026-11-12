import requests

# Test login with username
r = requests.post('http://localhost:8000/api/v1/auth/login/', json={'username':'testuser','password':'TestPassword123!'})
print(f"Status: {r.status_code}")
print(f"Response: {r.text}")
print(f"Headers: {r.headers}")
