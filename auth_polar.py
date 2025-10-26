import os
import json
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
from requests_oauthlib import OAuth2Session
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading

load_dotenv()
CLIENT_ID = os.getenv("POLAR_CLIENT_ID")
CLIENT_SECRET = os.getenv("POLAR_CLIENT_SECRET")

if not CLIENT_ID or not CLIENT_SECRET:
    raise ValueError("POLAR_CLIENT_ID or POLAR_CLIENT_SECRET not found in .env file")

REDIRECT_URI = "http://localhost:8080"
AUTHORIZATION_URL = "https://flow.polar.com/oauth2/authorization"
TOKEN_URL = "https://polarremote.com/v2/oauth2/token"

auth_code = None

class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        query = urlparse(self.path).query
        params = parse_qs(query)
        
        if 'code' in params:
            auth_code = params['code'][0]
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"<h1>Authorization successful!</h1><p>You can close this window and return to the terminal.</p>")
        else:
            self.send_response(400)
            self.end_headers()
    
    def log_message(self, format, *args):
        pass

def get_polar_token():
    global auth_code
    
    print("--- Polar Authentication ---")
    print(f"Client ID: {CLIENT_ID[:10]}...")
    
    server = HTTPServer(('localhost', 8080), CallbackHandler)
    server_thread = threading.Thread(target=server.handle_request)
    server_thread.daemon = True
    server_thread.start()
    
    polar_session = OAuth2Session(CLIENT_ID, redirect_uri=REDIRECT_URI)
    authorization_url, state = polar_session.authorization_url(AUTHORIZATION_URL)
    
    print(f"\nOpen this URL in your browser:\n\n{authorization_url}\n")
    print("Waiting for authorization...")
    
    server_thread.join(timeout=120)
    server.server_close()
    
    if not auth_code:
        print("\n✗ No authorization code received")
        return
    
    print("\n✓ Authorization code received!")
    print("Fetching access token...")
    
    token_data = {
        'grant_type': 'authorization_code',
        'code': auth_code,
        'redirect_uri': REDIRECT_URI
    }
    
    try:
        response = requests.post(
            TOKEN_URL,
            data=token_data,
            auth=HTTPBasicAuth(CLIENT_ID, CLIENT_SECRET)
        )
        
        if response.status_code == 200:
            token = response.json()
            
            with open("polar_token.json", "w") as f:
                json.dump(token, f, indent=2)
            
            print("\n✓ Success! Token saved to polar_token.json")
            print(f"Access token: {token['access_token'][:20]}...")
            
            # Register user for webhook notifications (required by Polar)
            register_user(token['access_token'], token['x_user_id'])
            
        else:
            print(f"\n✗ Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"\n✗ Error: {e}")

def register_user(access_token, user_id):
    """Register user for Polar AccessLink"""
    register_url = "https://www.polaraccesslink.com/v3/users"
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    data = {
        'member-id': str(user_id)
    }
    
    response = requests.post(register_url, headers=headers, json=data)
    
    if response.status_code == 200:
        print("✓ User registered with Polar AccessLink")
    elif response.status_code == 409:
        print("✓ User already registered with Polar AccessLink")
    else:
        print(f"⚠ User registration warning: {response.status_code}")
        print(f"Response: {response.text}")

if __name__ == "__main__":
    get_polar_token()