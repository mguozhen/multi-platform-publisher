#!/usr/bin/env python3
"""
LinkedIn OAuth 2.0 token fetcher.

Usage:
  export LI_CLIENT_ID=xxx
  export LI_CLIENT_SECRET=xxx
  python3 li-oauth.py

Opens browser → Hunter clicks Allow → token saved to ~/.secrets/linkedin.env
"""
import http.server
import os
import secrets
import socketserver
import sys
import threading
import urllib.parse
import webbrowser
from pathlib import Path

import requests

CLIENT_ID = os.environ.get("LI_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("LI_CLIENT_SECRET", "")
REDIRECT_URI = "http://localhost:8765/callback"
SCOPES = "openid profile w_member_social email"

if not CLIENT_ID or not CLIENT_SECRET:
    print("ERROR: Set LI_CLIENT_ID and LI_CLIENT_SECRET", file=sys.stderr)
    sys.exit(1)

state_token = secrets.token_urlsafe(16)
auth_code_holder = {"code": None, "state": None, "error": None}


class CallbackHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args): return  # quiet

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/callback":
            self.send_response(404)
            self.end_headers()
            return
        q = urllib.parse.parse_qs(parsed.query)
        if "error" in q:
            auth_code_holder["error"] = q.get("error_description", q.get("error", [""]))[0]
            html = f"<h1>❌ Error</h1><pre>{auth_code_holder['error']}</pre>"
        elif "code" in q and q.get("state", [""])[0] == state_token:
            auth_code_holder["code"] = q["code"][0]
            html = "<h1>✅ Got it. You can close this tab.</h1>"
        else:
            auth_code_holder["error"] = "state mismatch or missing code"
            html = f"<h1>❌</h1><pre>{auth_code_holder['error']}</pre>"
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode())


def start_server():
    with socketserver.TCPServer(("localhost", 8765), CallbackHandler) as httpd:
        while auth_code_holder["code"] is None and auth_code_holder["error"] is None:
            httpd.handle_request()


def build_auth_url():
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "state": state_token,
        "scope": SCOPES,
    }
    return f"https://www.linkedin.com/oauth/v2/authorization?{urllib.parse.urlencode(params)}"


def exchange_code_for_token(code: str) -> dict:
    r = requests.post(
        "https://www.linkedin.com/oauth/v2/accessToken",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


def fetch_userinfo(access_token: str) -> dict:
    r = requests.get(
        "https://api.linkedin.com/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


def save_secrets(env: dict):
    secrets_dir = Path.home() / ".secrets"
    secrets_dir.mkdir(mode=0o700, exist_ok=True)
    f = secrets_dir / "linkedin.env"
    lines = [f"# LinkedIn OAuth — generated {os.popen('date').read().strip()}"]
    for k, v in env.items():
        lines.append(f"{k}={v}")
    f.write_text("\n".join(lines) + "\n")
    f.chmod(0o600)
    print(f"✅ Saved to {f}")


def main():
    server = threading.Thread(target=start_server, daemon=True)
    server.start()

    url = build_auth_url()
    print(f"Opening browser…\n  {url}\n")
    webbrowser.open(url)

    # wait for callback
    import time
    while auth_code_holder["code"] is None and auth_code_holder["error"] is None:
        time.sleep(0.3)

    if auth_code_holder["error"]:
        print(f"❌ {auth_code_holder['error']}")
        sys.exit(1)

    print("✅ Got authorization code, exchanging for access token...")
    token = exchange_code_for_token(auth_code_holder["code"])
    access_token = token["access_token"]
    expires_in = token.get("expires_in", 0)
    refresh_token = token.get("refresh_token", "")

    print(f"   access_token: {access_token[:20]}... (expires in {expires_in}s = {expires_in//86400} days)")

    # Get person URN
    userinfo = fetch_userinfo(access_token)
    sub = userinfo["sub"]
    person_urn = f"urn:li:person:{sub}"
    print(f"   person URN:   {person_urn}")
    print(f"   name:         {userinfo.get('name', '?')}")

    save_secrets({
        "LINKEDIN_CLIENT_ID": CLIENT_ID,
        "LINKEDIN_CLIENT_SECRET": CLIENT_SECRET,
        "LINKEDIN_ACCESS_TOKEN": access_token,
        "LINKEDIN_REFRESH_TOKEN": refresh_token,
        "LINKEDIN_PERSON_URN": person_urn,
        "LINKEDIN_EXPIRES_IN": str(expires_in),
    })


if __name__ == "__main__":
    main()
