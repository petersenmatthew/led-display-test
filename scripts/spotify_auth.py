#!/usr/bin/env python3
"""One-time Spotify OAuth setup for scripts/spotify.py.

Run this once (on the Pi over SSH or on your laptop — the resulting
spotify_config.json just needs to end up at the repo root):

    python3 scripts/spotify_auth.py

Prerequisites:
  1. Go to https://developer.spotify.com/dashboard and create an app.
  2. In the app settings, add this Redirect URI exactly:
         http://127.0.0.1:8888/callback
  3. Copy the Client ID and Client Secret; this script asks for them.

The browser will fail to load the redirect page (nothing listens on
127.0.0.1:8888) — that's expected. Copy the full URL from the address
bar and paste it here.
"""

from __future__ import annotations

import base64
import json
import os
import urllib.parse
import urllib.request
import webbrowser

REDIRECT_URI = "http://127.0.0.1:8888/callback"
SCOPES = "user-read-currently-playing user-read-playback-state"
AUTH_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(REPO_ROOT, "spotify_config.json")


def prompt(label, default=None):
    suffix = " [%s]" % default if default else ""
    value = input("%s%s: " % (label, suffix)).strip()
    return value or default or ""


def exchange_code(client_id, client_secret, code):
    body = urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
    }).encode()
    auth = base64.b64encode(("%s:%s" % (client_id, client_secret)).encode()).decode()
    req = urllib.request.Request(TOKEN_URL, data=body, headers={
        "Authorization": "Basic " + auth,
        "Content-Type": "application/x-www-form-urlencoded",
    })
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def verify(client_id, client_secret, refresh_token):
    """Refresh once and hit the now-playing endpoint to prove it works."""
    body = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }).encode()
    auth = base64.b64encode(("%s:%s" % (client_id, client_secret)).encode()).decode()
    req = urllib.request.Request(TOKEN_URL, data=body, headers={
        "Authorization": "Basic " + auth,
        "Content-Type": "application/x-www-form-urlencoded",
    })
    with urllib.request.urlopen(req, timeout=15) as resp:
        access_token = json.loads(resp.read().decode("utf-8"))["access_token"]

    req = urllib.request.Request(
        "https://api.spotify.com/v1/me/player/currently-playing",
        headers={"Authorization": "Bearer " + access_token},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        if resp.status == 204:
            return "authorized (nothing playing right now)"
        data = json.loads(resp.read().decode("utf-8"))
    item = data.get("item") or {}
    return "authorized — now playing: %s" % item.get("name", "?")


def main():
    print(__doc__)

    existing = {}
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH) as fh:
                existing = json.load(fh)
            print("Found existing %s — press Enter to reuse values.\n" % CONFIG_PATH)
        except (OSError, ValueError):
            pass

    client_id = prompt("Client ID", existing.get("client_id"))
    client_secret = prompt("Client Secret", existing.get("client_secret"))
    if not client_id or not client_secret:
        raise SystemExit("Client ID and Client Secret are required.")

    params = urllib.parse.urlencode({
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
    })
    url = "%s?%s" % (AUTH_URL, params)
    print("\nOpen this URL in a browser and click Agree:\n\n%s\n" % url)
    try:
        webbrowser.open(url)
    except Exception:
        pass

    pasted = input(
        "After approving, paste the full URL from the address bar\n"
        "(starts with %s): " % REDIRECT_URI
    ).strip()
    if "code=" in pasted:
        query = urllib.parse.urlparse(pasted).query
        code = urllib.parse.parse_qs(query).get("code", [""])[0]
    else:
        code = pasted  # allow pasting just the code
    if not code:
        raise SystemExit("No authorization code found in that URL.")

    tokens = exchange_code(client_id, client_secret, code)
    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        raise SystemExit("Spotify did not return a refresh token: %s" % tokens)

    config = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
    }
    with open(CONFIG_PATH, "w") as fh:
        json.dump(config, fh, indent=2)
    os.chmod(CONFIG_PATH, 0o600)
    print("\nSaved %s" % CONFIG_PATH)

    try:
        print(verify(client_id, client_secret, refresh_token))
    except Exception as exc:
        print("Saved, but the verification call failed: %s" % exc)
    print("\nDone. Select 'spotify' in the control panel to start the display.")


if __name__ == "__main__":
    main()
