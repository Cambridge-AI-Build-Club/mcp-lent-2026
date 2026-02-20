# Spotify MCP Server Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a 3-tool Spotify MCP server (get_current_song, search_track, create_playlist) with built-in OAuth authorization flow.

**Architecture:** MCP server split into two modules: `auth.py` handles OAuth 2.0 Authorization Code flow with localhost callback and token persistence, `server.py` defines the 3 tools and calls the Spotify Web API via httpx. Tokens are stored in `~/.spotify_mcp_tokens.json` and auto-refreshed.

**Tech Stack:** Python 3.14, MCP SDK (`mcp`), `httpx`, stdlib `http.server` + `webbrowser` for OAuth

---

### Task 1: Add httpx dependency

**Files:**
- Modify: `spotify_mcp/pyproject.toml`

**Step 1: Add httpx to dependencies**

In `spotify_mcp/pyproject.toml`, change:
```toml
dependencies = [ "mcp>=1.26.0",]
```
to:
```toml
dependencies = [
    "httpx>=0.27.0",
    "mcp>=1.26.0",
]
```

**Step 2: Sync dependencies**

Run: `cd spotify_mcp && uv sync`
Expected: lockfile updates, httpx installed

**Step 3: Commit**

```bash
git add spotify_mcp/pyproject.toml spotify_mcp/uv.lock
git commit -m "feat(spotify): add httpx dependency"
```

---

### Task 2: Implement OAuth auth module

**Files:**
- Create: `spotify_mcp/src/spotify_mcp/auth.py`

**Step 1: Create auth.py**

```python
import json
import os
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx

SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
REDIRECT_URI = "http://localhost:8888/callback"
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

    auth_url = (
        f"{SPOTIFY_AUTH_URL}?response_type=code"
        f"&client_id={client_id}"
        f"&scope={SCOPES.replace(' ', '%20')}"
        f"&redirect_uri={REDIRECT_URI.replace(':', '%3A').replace('/', '%2F')}"
    )

    server = HTTPServer(("localhost", 8888), _CallbackHandler)
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
```

**Step 2: Commit**

```bash
git add spotify_mcp/src/spotify_mcp/auth.py
git commit -m "feat(spotify): implement OAuth auth module with token persistence"
```

---

### Task 3: Implement the 3 Spotify tools

**Files:**
- Modify: `spotify_mcp/src/spotify_mcp/server.py` (replace entire contents)

**Step 1: Replace server.py**

```python
import httpx
import mcp.server.stdio
import mcp.types as types
from mcp.server import Server

from . import auth

server = Server("spotify_mcp")

SPOTIFY_API = "https://api.spotify.com/v1"


async def _spotify_get(path: str, params: dict | None = None) -> httpx.Response:
    token = await auth.get_access_token()
    async with httpx.AsyncClient() as client:
        return await client.get(
            f"{SPOTIFY_API}{path}",
            params=params,
            headers={"Authorization": f"Bearer {token}"},
        )


async def _spotify_post(path: str, json_body: dict) -> httpx.Response:
    token = await auth.get_access_token()
    async with httpx.AsyncClient() as client:
        return await client.post(
            f"{SPOTIFY_API}{path}",
            json=json_body,
            headers={"Authorization": f"Bearer {token}"},
        )


async def get_current_song() -> str:
    response = await _spotify_get("/me/player/currently-playing")

    if response.status_code == 204 or not response.content:
        return "Nothing is currently playing."

    if response.status_code != 200:
        return f"Spotify API error (status {response.status_code}): {response.text}"

    data = response.json()
    if not data.get("item"):
        return "Nothing is currently playing."

    track = data["item"]
    artists = ", ".join(a["name"] for a in track["artists"])
    progress_s = data.get("progress_ms", 0) // 1000
    duration_s = track["duration_ms"] // 1000
    progress_fmt = f"{progress_s // 60}:{progress_s % 60:02d}"
    duration_fmt = f"{duration_s // 60}:{duration_s % 60:02d}"

    return (
        f"Now Playing:\n"
        f"  Track: {track['name']}\n"
        f"  Artist: {artists}\n"
        f"  Album: {track['album']['name']}\n"
        f"  Progress: {progress_fmt} / {duration_fmt}"
    )


async def search_track(query: str) -> str:
    response = await _spotify_get("/search", params={"q": query, "type": "track", "limit": 5})

    if response.status_code != 200:
        return f"Spotify API error (status {response.status_code}): {response.text}"

    data = response.json()
    tracks = data.get("tracks", {}).get("items", [])

    if not tracks:
        return f"No results found for: {query}"

    lines = [f"Search results for '{query}':\n"]
    for i, track in enumerate(tracks, 1):
        artists = ", ".join(a["name"] for a in track["artists"])
        lines.append(
            f"  {i}. {track['name']} — {artists}\n"
            f"     Album: {track['album']['name']}\n"
            f"     URI: {track['uri']}"
        )

    return "\n".join(lines)


async def create_playlist(name: str) -> str:
    # Get user ID first
    user_response = await _spotify_get("/me")
    if user_response.status_code != 200:
        return f"Failed to get user profile (status {user_response.status_code}): {user_response.text}"

    user_id = user_response.json()["id"]

    response = await _spotify_post(
        f"/users/{user_id}/playlists",
        json_body={"name": name, "public": False},
    )

    if response.status_code not in (200, 201):
        return f"Failed to create playlist (status {response.status_code}): {response.text}"

    data = response.json()
    return (
        f"Playlist created!\n"
        f"  Name: {data['name']}\n"
        f"  URL: {data['external_urls']['spotify']}"
    )


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="get_current_song",
            description="Get the currently playing song on Spotify",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        types.Tool(
            name="search_track",
            description="Search for tracks on Spotify",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query, e.g. 'Bohemian Rhapsody' or 'artist:Queen'",
                    },
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="create_playlist",
            description="Create a new empty playlist on Spotify",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name for the new playlist",
                    },
                },
                "required": ["name"],
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent]:
    match name:
        case "get_current_song":
            result = await get_current_song()
        case "search_track":
            if not arguments or "query" not in arguments:
                raise ValueError("Missing required argument: query")
            result = await search_track(arguments["query"])
        case "create_playlist":
            if not arguments or "name" not in arguments:
                raise ValueError("Missing required argument: name")
            result = await create_playlist(arguments["name"])
        case _:
            raise ValueError(f"Unknown tool: {name}")

    return [types.TextContent(type="text", text=result)]


async def main():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())
```

**Step 2: Commit**

```bash
git add spotify_mcp/src/spotify_mcp/server.py
git commit -m "feat(spotify): implement get_current_song, search_track, create_playlist tools"
```

---

### Task 4: Write tests

**Files:**
- Modify: `spotify_mcp/pyproject.toml` (add test deps)
- Create: `spotify_mcp/tests/__init__.py`
- Create: `spotify_mcp/tests/test_auth.py`
- Create: `spotify_mcp/tests/test_server.py`

**Step 1: Add test dependencies**

Add to `spotify_mcp/pyproject.toml` after `[build-system]`:

```toml
[dependency-groups]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.25",
]
```

Run: `cd spotify_mcp && uv sync`

**Step 2: Create test files**

Create `spotify_mcp/tests/__init__.py` (empty).

Create `spotify_mcp/tests/test_auth.py`:

```python
import json
from pathlib import Path
from unittest.mock import patch

from spotify_mcp.auth import _load_tokens, _save_tokens


def test_save_and_load_tokens(tmp_path):
    token_file = tmp_path / "tokens.json"
    tokens = {"access_token": "abc", "refresh_token": "xyz"}

    with patch("spotify_mcp.auth.TOKEN_PATH", token_file):
        _save_tokens(tokens)
        loaded = _load_tokens()

    assert loaded == tokens


def test_load_tokens_missing(tmp_path):
    token_file = tmp_path / "nonexistent.json"
    with patch("spotify_mcp.auth.TOKEN_PATH", token_file):
        assert _load_tokens() is None


def test_get_credentials_missing(monkeypatch):
    monkeypatch.delenv("SPOTIFY_CLIENT_ID", raising=False)
    monkeypatch.delenv("SPOTIFY_CLIENT_SECRET", raising=False)

    from spotify_mcp.auth import _get_credentials
    import pytest

    with pytest.raises(RuntimeError, match="SPOTIFY_CLIENT_ID"):
        _get_credentials()


def test_get_credentials_present(monkeypatch):
    monkeypatch.setenv("SPOTIFY_CLIENT_ID", "test-id")
    monkeypatch.setenv("SPOTIFY_CLIENT_SECRET", "test-secret")

    from spotify_mcp.auth import _get_credentials

    cid, csecret = _get_credentials()
    assert cid == "test-id"
    assert csecret == "test-secret"
```

Create `spotify_mcp/tests/test_server.py`:

```python
from unittest.mock import AsyncMock, patch

import pytest

from spotify_mcp.server import get_current_song, search_track, create_playlist


@pytest.mark.asyncio
async def test_get_current_song_playing():
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.content = b"data"
    mock_response.json.return_value = {
        "item": {
            "name": "Bohemian Rhapsody",
            "artists": [{"name": "Queen"}],
            "album": {"name": "A Night at the Opera"},
            "duration_ms": 354000,
        },
        "progress_ms": 120000,
    }

    with patch("spotify_mcp.server._spotify_get", return_value=mock_response):
        result = await get_current_song()

    assert "Bohemian Rhapsody" in result
    assert "Queen" in result
    assert "A Night at the Opera" in result
    assert "2:00" in result


@pytest.mark.asyncio
async def test_get_current_song_nothing_playing():
    mock_response = AsyncMock()
    mock_response.status_code = 204
    mock_response.content = b""

    with patch("spotify_mcp.server._spotify_get", return_value=mock_response):
        result = await get_current_song()

    assert "Nothing is currently playing" in result


@pytest.mark.asyncio
async def test_search_track_results():
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "tracks": {
            "items": [
                {
                    "name": "Bohemian Rhapsody",
                    "artists": [{"name": "Queen"}],
                    "album": {"name": "A Night at the Opera"},
                    "uri": "spotify:track:abc123",
                },
            ]
        }
    }

    with patch("spotify_mcp.server._spotify_get", return_value=mock_response):
        result = await search_track("Bohemian Rhapsody")

    assert "Bohemian Rhapsody" in result
    assert "Queen" in result
    assert "spotify:track:abc123" in result


@pytest.mark.asyncio
async def test_search_track_no_results():
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"tracks": {"items": []}}

    with patch("spotify_mcp.server._spotify_get", return_value=mock_response):
        result = await search_track("xyznonexistent")

    assert "No results found" in result


@pytest.mark.asyncio
async def test_create_playlist_success():
    user_response = AsyncMock()
    user_response.status_code = 200
    user_response.json.return_value = {"id": "user123"}

    playlist_response = AsyncMock()
    playlist_response.status_code = 201
    playlist_response.json.return_value = {
        "name": "My Playlist",
        "external_urls": {"spotify": "https://open.spotify.com/playlist/abc"},
    }

    with (
        patch("spotify_mcp.server._spotify_get", return_value=user_response),
        patch("spotify_mcp.server._spotify_post", return_value=playlist_response),
    ):
        result = await create_playlist("My Playlist")

    assert "My Playlist" in result
    assert "https://open.spotify.com/playlist/abc" in result
```

**Step 3: Run tests**

Run: `cd spotify_mcp && uv run pytest tests/ -v`
Expected: 8 tests PASS (4 auth + 4 server — but test_get_current_song has 2 cases so actually: 4 auth + 5 server = 9 total... let me recount: test_auth has 4 tests, test_server has 5 tests = 9 total)

**Step 4: Commit**

```bash
git add spotify_mcp/tests/ spotify_mcp/pyproject.toml spotify_mcp/uv.lock
git commit -m "test(spotify): add unit tests for auth and server"
```

---

### Task 5: Update README

**Files:**
- Modify: `spotify_mcp/README.md`

**Step 1: Replace README**

```markdown
# spotify_mcp MCP Server

An MCP server that connects to your Spotify account for playback info, search, and playlist creation.

## Tools

### get_current_song

Get the currently playing track on Spotify.

- **Input:** none
- **Output:** Track name, artist, album, playback progress

### search_track

Search for tracks on Spotify.

- **Input:** `query` (string, required) — e.g. "Bohemian Rhapsody" or "artist:Queen"
- **Output:** Top 5 results with name, artist, album, Spotify URI

### create_playlist

Create a new empty playlist.

- **Input:** `name` (string, required) — playlist name
- **Output:** Playlist name and Spotify URL

## Setup

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard) and create an app
2. Set the redirect URI to `http://localhost:8888/callback` in your app settings
3. Note your Client ID and Client Secret

## Configuration

### Claude Desktop

On MacOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
On Windows: `%APPDATA%/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "spotify_mcp": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/spotify_mcp",
        "run",
        "spotify-mcp"
      ],
      "env": {
        "SPOTIFY_CLIENT_ID": "your_client_id",
        "SPOTIFY_CLIENT_SECRET": "your_client_secret"
      }
    }
  }
}
```

## First Run

On first use, the server will open your browser for Spotify authorization. After approving, tokens are saved to `~/.spotify_mcp_tokens.json` and reused automatically.

## Development

```bash
uv sync
uv run pytest tests/ -v
```
```

**Step 2: Commit**

```bash
git add spotify_mcp/README.md
git commit -m "docs(spotify): update README with setup and usage instructions"
```

---

### Task 6: Manual smoke test

**Step 1: Run with MCP Inspector**

Run: `cd spotify_mcp && SPOTIFY_CLIENT_ID=your_id SPOTIFY_CLIENT_SECRET=your_secret npx @modelcontextprotocol/inspector uv run spotify-mcp`

**Step 2: In the Inspector UI:**
- Verify all 3 tools appear in the tools list
- Call `get_current_song` (have Spotify playing something)
- Call `search_track` with `{"query": "Bohemian Rhapsody"}`
- Call `create_playlist` with `{"name": "MCP Test Playlist"}`
- Delete the test playlist from Spotify afterwards
