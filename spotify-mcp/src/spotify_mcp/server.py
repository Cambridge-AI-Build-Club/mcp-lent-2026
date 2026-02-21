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
