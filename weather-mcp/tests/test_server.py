from unittest.mock import AsyncMock, patch

import pytest

from weather_mcp.server import fetch_weather


@pytest.fixture
def mock_weather_response():
    return {
        "name": "London",
        "weather": [{"description": "light rain"}],
        "main": {"temp": 12.5, "humidity": 82},
        "wind": {"speed": 4.1},
    }


@pytest.mark.asyncio
async def test_fetch_weather_success(mock_weather_response, monkeypatch):
    monkeypatch.setenv("OPENWEATHER_API_KEY", "test-key")

    mock_response = AsyncMock()
    mock_response.status_code = 200
    # Make json() a regular method that returns the dict
    mock_response.json = lambda: mock_weather_response

    with patch("weather_mcp.server.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await fetch_weather("London")

    assert "London" in result
    assert "12.5°C" in result
    assert "light rain" in result
    assert "82%" in result
    assert "4.1 m/s" in result


@pytest.mark.asyncio
async def test_fetch_weather_missing_api_key(monkeypatch):
    monkeypatch.delenv("OPENWEATHER_API_KEY", raising=False)
    result = await fetch_weather("London")
    assert "OPENWEATHER_API_KEY" in result
    assert "not set" in result


@pytest.mark.asyncio
async def test_fetch_weather_city_not_found(monkeypatch):
    monkeypatch.setenv("OPENWEATHER_API_KEY", "test-key")

    mock_response = AsyncMock()
    mock_response.status_code = 404

    with patch("weather_mcp.server.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await fetch_weather("FakeCity123")

    assert "City not found" in result
