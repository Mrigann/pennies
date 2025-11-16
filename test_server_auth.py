"""Test server authentication."""
import requests
import json

print("Testing server authentication...")
print("=" * 50)

try:
    # Test debug endpoint
    r = requests.get('http://127.0.0.1:5000/api/debug/auth', timeout=5)
    print(f"Status Code: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print("\nAuthentication Debug Info:")
        print(f"  .env file exists: {data.get('env_file_exists')}")
        print(f"  API Key loaded: {data.get('api_key_loaded')}")
        print(f"  Secret Key loaded: {data.get('secret_key_loaded')}")
        print(f"  API Key length: {data.get('api_key_length')}")
        print(f"  Auth test: {data.get('auth_test')}")
        if data.get('auth_test') == 'SUCCESS':
            print(f"  Account: {data.get('account_number')}")
            print("\n✓ Authentication is working!")
        else:
            print(f"  Error: {data.get('auth_error')}")
            print("\n✗ Authentication failed")
    else:
        print(f"Error: {r.text}")
except requests.exceptions.ConnectionError:
    print("✗ Cannot connect to server. Is it running?")
    print("  Start it with: python web/app.py")
except Exception as e:
    print(f"✗ Error: {e}")

print("=" * 50)

