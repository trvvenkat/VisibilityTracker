import json
import os
import sys
import time
import urllib.error
import urllib.request

NGROK_API = os.getenv("NGROK_API_URL", "http://ngrok:4040")
AUTH_USER = os.getenv("AUTH_USERNAME", "admin")
AUTH_PASS = os.getenv("AUTH_PASSWORD", "tracker@2026")


def check_tunnels():
    url = f"{NGROK_API.rstrip('/')}/api/tunnels"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "VisibilityTracker-Watcher/1.0"})
        with urllib.request.urlopen(req, timeout=2.0) as res:
            if res.status == 200:
                data = json.loads(res.read().decode("utf-8"))
                tunnels = data.get("tunnels", [])
                if tunnels:
                    https_t = next((t for t in tunnels if t.get("proto") == "https"), tunnels[0])
                    return https_t.get("public_url")
    except Exception:
        pass
    return None


def main():
    print("\n⏳ Waiting for ngrok tunnel to establish connection...", flush=True)

    max_attempts = 40
    public_url = None

    for _ in range(max_attempts):
        public_url = check_tunnels()
        if public_url:
            break
        time.sleep(1.0)

    if public_url:
        banner = f"""
================================================================================
🚀  VISIBILITY CHECK TRACKER IS LIVE & READY!
================================================================================

📱  TABLET / LAPTOP REMOTE ACCESS URL:
    👉  {public_url}  👈

💻  LOCAL ACCESS URL:
    http://localhost:8000  (or http://127.0.0.1:8000)

🔑  LOGIN CREDENTIALS:
    Username: {AUTH_USER}
    Password: {AUTH_PASS}

💡  USAGE TIPS:
    • Open the Remote Access URL on any laptop, tablet, or phone.
    • You can also click 'Copy' in the top dashboard navigation to share.
    • Press Ctrl+C in this terminal window anytime to stop the server.

================================================================================
"""
        print(banner, flush=True)
    else:
        warn = f"""
================================================================================
⚠️  NOTICE: NGROK TUNNEL COULD NOT BE DETECTED
================================================================================
The local Visibility Tracker is running at: http://localhost:8000

If using ngrok, please check that NGROK_AUTHTOKEN is configured in your .env file:
Get a free token in 1 minute at: https://dashboard.ngrok.com/get-started/your-authtoken

Login credentials:
Username: {AUTH_USER}
Password: {AUTH_PASS}
================================================================================
"""
        print(warn, flush=True)

    # Keep container alive to display status
    while True:
        time.sleep(3600)


if __name__ == "__main__":
    main()
