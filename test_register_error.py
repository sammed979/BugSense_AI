import requests

# Test registration
r = requests.post('http://localhost:8000/api/v1/auth/register/', 
                  json={'username':'sam','email':'badboyvikki99@gmail.com','password':'Test123!','confirm_password':'Test123!'})
print(f"Status: {r.status_code}")
print(f"Response: {r.text}")
