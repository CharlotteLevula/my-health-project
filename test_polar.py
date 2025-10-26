import json
import requests

# Load the token
with open("polar_token.json", "r") as f:
    token = json.load(f)

access_token = token['access_token']
user_id = token['x_user_id']

# Test API call - get user information
headers = {'Authorization': f'Bearer {access_token}'}
response = requests.get(f"https://www.polaraccesslink.com/v3/users/{user_id}", headers=headers)

if response.status_code == 200:
    print("✓ Polar authentication successful!")
    print(f"User data: {response.json()}")
else:
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
