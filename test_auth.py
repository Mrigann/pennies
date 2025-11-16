"""Test script to verify Alpaca authentication."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from config import settings
from trading.alpaca_client import AlpacaClient

print("=" * 50)
print("Testing Alpaca Authentication")
print("=" * 50)
print(f"API Key loaded: {bool(settings.ALPACA_API_KEY)}")
print(f"Secret Key loaded: {bool(settings.ALPACA_SECRET_KEY)}")
print(f"API Key: {settings.ALPACA_API_KEY[:15]}...")
print()

try:
    print("Creating AlpacaClient...")
    client = AlpacaClient()
    print("✓ Client created successfully")
    
    print("Testing authentication...")
    account = client.get_account()
    print(f"✓ Authentication successful!")
    print(f"  Account Number: {account['account_number']}")
    print(f"  Portfolio Value: ${account['portfolio_value']:.2f}")
    print(f"  Buying Power: ${account['buying_power']:.2f}")
    print()
    print("=" * 50)
    print("✓ All tests passed! Authentication is working.")
    print("=" * 50)
except Exception as e:
    print(f"✗ Error: {e}")
    print()
    print("Troubleshooting:")
    print("1. Check that .env file exists in project root")
    print("2. Verify API keys in .env file")
    print("3. Restart the web server after creating .env file")
    sys.exit(1)

