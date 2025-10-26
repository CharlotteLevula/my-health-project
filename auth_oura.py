import os
import requests
from dotenv import load_dotenv

load_dotenv()
ACCESS_TOKEN = os.getenv("OURA_ACCESS_TOKEN")

if not ACCESS_TOKEN:
    raise ValueError("OURA_ACCESS_TOKEN not found in .env file")

# Test the token
headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}

# Get personal info
response = requests.get("https://api.ouraring.com/v2/usercollection/personal_info", headers=headers)

if response.status_code == 200:
    print("✓ Authentication successful!")
    print(f"User data: {response.json()}")
else:
    print(f"✗ Error: {response.status_code}")
    print(response.text)