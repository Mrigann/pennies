# Quick Fix for Authentication Error

## The Problem
You're seeing "You must supply a method of authentication" error.

## The Solution

**The API keys are now hardcoded in `config/settings.py` as a fallback**, so they will ALWAYS be available.

## Steps to Fix:

1. **STOP the current server** (Press Ctrl+C in the terminal)

2. **RESTART the server:**
   ```bash
   python web/app.py
   ```

3. **Look for these messages when it starts:**
   - `API Key loaded: PK37L27LF5... (length: 26)`
   - `Secret Key loaded: GZqitSttHP... (length: 44)`
   - `[Web App] API keys loaded successfully at startup`

4. **Refresh your browser** - the dashboard should now work!

## If It Still Doesn't Work:

Check the server console output when you try to search for a stock. You should see:
- `Initializing trading system...`
- `Creating AlpacaClient with explicit keys...`
- `Authentication test successful. Account: PA3G8B2JARIC`

If you see errors, copy the console output and share it.

## Alternative: Use the Batch File

You can also use the `start_server.bat` file I created - just double-click it to start the server.


