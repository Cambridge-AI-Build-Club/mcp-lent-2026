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
