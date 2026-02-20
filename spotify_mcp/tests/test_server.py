from unittest.mock import AsyncMock, Mock, patch

import pytest

from spotify_mcp.server import get_current_song, search_track, create_playlist


@pytest.mark.asyncio
async def test_get_current_song_playing():
    mock_response = Mock()
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
    mock_response = Mock()
    mock_response.status_code = 204
    mock_response.content = b""

    with patch("spotify_mcp.server._spotify_get", return_value=mock_response):
        result = await get_current_song()

    assert "Nothing is currently playing" in result


@pytest.mark.asyncio
async def test_search_track_results():
    mock_response = Mock()
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
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"tracks": {"items": []}}

    with patch("spotify_mcp.server._spotify_get", return_value=mock_response):
        result = await search_track("xyznonexistent")

    assert "No results found" in result


@pytest.mark.asyncio
async def test_create_playlist_success():
    user_response = Mock()
    user_response.status_code = 200
    user_response.json.return_value = {"id": "user123"}

    playlist_response = Mock()
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
