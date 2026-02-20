# Spotify MCP Server Design

## Overview

Replace the template notes MCP server with a 3-tool Spotify server using httpx for API calls and a built-in localhost OAuth flow.

## Tools

| Tool | Input | Output |
|------|-------|--------|
| get_current_song | none | Currently playing track: name, artist, album, progress |
| search_track | query: string | Top 5 results: name, artist, album, Spotify URI |
| create_playlist | name: string | Created playlist name + URL |

## OAuth Flow

1. On first use, start temporary HTTP server on localhost:8888
2. Open browser to Spotify auth URL with scopes: user-read-currently-playing, playlist-modify-public, playlist-modify-private
3. User logs in — Spotify redirects to localhost:8888/callback
4. Capture auth code, exchange for access + refresh tokens
5. Save tokens to ~/.spotify_mcp_tokens.json
6. On subsequent starts, load from file and auto-refresh if expired

## Configuration

- SPOTIFY_CLIENT_ID env var
- SPOTIFY_CLIENT_SECRET env var
- Redirect URI: http://localhost:8888/callback (register in Spotify app settings)

## Spotify API Endpoints

- GET /v1/me/player/currently-playing
- GET /v1/search?type=track
- GET /v1/me (to get user ID for playlist creation)
- POST /v1/users/{user_id}/playlists

## Error Handling

- Missing credentials: clear error message
- No active playback: "Nothing is currently playing"
- Token expired: auto-refresh
- Refresh token invalid: prompt re-authorization
- No search results: "No results found"
- API errors: return status code and message

## Files

- server.py — 3 tools + MCP handlers
- auth.py — OAuth flow + token management
- pyproject.toml — add httpx
- README.md — Spotify setup instructions

## Decisions

- HTTP client: httpx (consistent with weather MCP)
- OAuth: manual Authorization Code flow with localhost callback
- Token storage: ~/.spotify_mcp_tokens.json
- Scopes: minimal set for the 3 tools
