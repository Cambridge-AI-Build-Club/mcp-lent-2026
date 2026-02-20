import json
import os
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
REDIRECT_URI = "http://127.0.0.1:8888/callback"
SCOPES = "user-read-currently-playing playlist-modify-public playlist-modify-private"
TOKEN_PATH = Path.home() / ".spotify_mcp_tokens.json"


def _get_credentials() -> tuple[str, str]:
    client_id = os.environ.get("SPOTIFY_CLIENT_ID")
    client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise RuntimeError(
            "SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET environment variables must be set."
        )
    return client_id, client_secret


def _save_tokens(tokens: dict) -> None:
    TOKEN_PATH.write_text(json.dumps(tokens))


def _load_tokens() -> dict | None:
    if TOKEN_PATH.exists():
        return json.loads(TOKEN_PATH.read_text())
    return None


class _CallbackHandler(BaseHTTPRequestHandler):
    auth_code: str | None = None

    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        if "code" in query:
            _CallbackHandler.auth_code = query["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h1>Authorization successful!</h1><p>You can close this tab.</p>")
        else:
            error = query.get("error", ["unknown"])[0]
            self.send_response(400)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(f"<h1>Authorization failed: {error}</h1>".encode())

    def log_message(self, format, *args):
        pass  # Suppress request logs


def authorize() -> dict:
    """Run the OAuth flow: open browser, capture callback, exchange code for tokens."""
    client_id, client_secret = _get_credentials()

    params = urlencode({
        "response_type": "code",
        "client_id": client_id,
        "scope": SCOPES,
        "redirect_uri": REDIRECT_URI,
    })
    auth_url = f"{SPOTIFY_AUTH_URL}?{params}"

    server = HTTPServer(("127.0.0.1", 8888), _CallbackHandler)
    _CallbackHandler.auth_code = None

    thread = threading.Thread(target=server.handle_request)
    thread.start()

    webbrowser.open(auth_url)
    thread.join(timeout=120)
    server.server_close()

    if not _CallbackHandler.auth_code:
        raise RuntimeError("Authorization timed out or failed.")

    response = httpx.post(
        SPOTIFY_TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": _CallbackHandler.auth_code,
            "redirect_uri": REDIRECT_URI,
        },
        auth=(client_id, client_secret),
    )
    response.raise_for_status()
    tokens = response.json()
    _save_tokens(tokens)
    return tokens


def refresh_access_token(refresh_token: str) -> dict:
    """Exchange a refresh token for a new access token."""
    client_id, client_secret = _get_credentials()

    response = httpx.post(
        SPOTIFY_TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
        auth=(client_id, client_secret),
    )
    response.raise_for_status()
    new_tokens = response.json()
    # Spotify may or may not return a new refresh token
    if "refresh_token" not in new_tokens:
        new_tokens["refresh_token"] = refresh_token
    _save_tokens(new_tokens)
    return new_tokens


async def get_access_token() -> str:
    """Get a valid access token, refreshing or re-authorizing as needed."""
    tokens = _load_tokens()

    if not tokens:
        tokens = authorize()
        return tokens["access_token"]

    # Try using existing token first; if it fails we'll refresh
    async with httpx.AsyncClient() as client:
        test = await client.get(
            "https://api.spotify.com/v1/me",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )

    if test.status_code == 401:
        tokens = refresh_access_token(tokens["refresh_token"])

    return tokens["access_token"]
