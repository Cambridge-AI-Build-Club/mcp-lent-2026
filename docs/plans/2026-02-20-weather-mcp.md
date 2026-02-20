# Weather MCP Server Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the template notes MCP server with a `get_weather(city)` tool that calls OpenWeatherMap's Current Weather API.

**Architecture:** Single-tool MCP server using `httpx` for async HTTP calls to OpenWeatherMap. API key read from `OPENWEATHER_API_KEY` env var. Returns formatted text with temp, description, humidity, wind speed.

**Tech Stack:** Python 3.14, MCP SDK (`mcp`), `httpx`, `pytest`, `pytest-asyncio`

---

### Task 1: Add httpx dependency

**Files:**
- Modify: `weather_mcp/pyproject.toml`

**Step 1: Add httpx to dependencies**

In `pyproject.toml`, change:
```toml
dependencies = [
    "mcp>=1.26.0",
]
```
to:
```toml
dependencies = [
    "httpx>=0.27.0",
    "mcp>=1.26.0",
]
```

**Step 2: Sync dependencies**

Run: `cd weather_mcp && uv sync`
Expected: lockfile updates, httpx installed

**Step 3: Commit**

```bash
git add weather_mcp/pyproject.toml weather_mcp/uv.lock
git commit -m "feat: add httpx dependency for weather API calls"
```

---

### Task 2: Write the get_weather tool implementation

**Files:**
- Modify: `weather_mcp/src/weather_mcp/server.py` (replace entire contents)

**Step 1: Replace server.py with weather implementation**

Replace the entire contents of `server.py` with:

```python
import os

import httpx
import mcp.server.stdio
import mcp.types as types
from mcp.server import Server

server = Server("weather_mcp")

OPENWEATHER_API_URL = "https://api.openweathermap.org/data/2.5/weather"


async def fetch_weather(city: str) -> str:
    """Call OpenWeatherMap API and return formatted weather string."""
    api_key = os.environ.get("OPENWEATHER_API_KEY")
    if not api_key:
        return "Error: OPENWEATHER_API_KEY environment variable is not set."

    params = {
        "q": city,
        "appid": api_key,
        "units": "metric",
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(OPENWEATHER_API_URL, params=params)

    if response.status_code == 404:
        return f"City not found: {city}"
    if response.status_code != 200:
        return f"API error (status {response.status_code}): {response.text}"

    data = response.json()
    weather_desc = data["weather"][0]["description"]
    temp = data["main"]["temp"]
    humidity = data["main"]["humidity"]
    wind_speed = data["wind"]["speed"]

    return (
        f"Weather in {data['name']}:\n"
        f"  Temperature: {temp}°C\n"
        f"  Conditions: {weather_desc}\n"
        f"  Humidity: {humidity}%\n"
        f"  Wind Speed: {wind_speed} m/s"
    )


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="get_weather",
            description="Get current weather for a city using OpenWeatherMap",
            inputSchema={
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "City name, e.g. 'London' or 'Tokyo,JP'",
                    },
                },
                "required": ["city"],
            },
        )
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent]:
    if name != "get_weather":
        raise ValueError(f"Unknown tool: {name}")

    if not arguments or "city" not in arguments:
        raise ValueError("Missing required argument: city")

    result = await fetch_weather(arguments["city"])
    return [types.TextContent(type="text", text=result)]


async def main():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())
```

**Step 2: Commit**

```bash
git add weather_mcp/src/weather_mcp/server.py
git commit -m "feat: implement get_weather tool with OpenWeatherMap API"
```

---

### Task 3: Write tests

**Files:**
- Create: `weather_mcp/tests/__init__.py`
- Create: `weather_mcp/tests/test_server.py`
- Modify: `weather_mcp/pyproject.toml` (add test deps)

**Step 1: Add test dependencies to pyproject.toml**

Add after `[build-system]` section:

```toml
[dependency-groups]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.25",
]
```

Run: `cd weather_mcp && uv sync`

**Step 2: Create test file**

Create `weather_mcp/tests/__init__.py` (empty file).

Create `weather_mcp/tests/test_server.py`:

```python
from unittest.mock import AsyncMock, patch

import httpx
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
    mock_response.json.return_value = mock_weather_response

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
```

**Step 3: Run tests**

Run: `cd weather_mcp && uv run pytest tests/ -v`
Expected: 3 tests PASS

**Step 4: Commit**

```bash
git add weather_mcp/tests/ weather_mcp/pyproject.toml weather_mcp/uv.lock
git commit -m "test: add unit tests for fetch_weather"
```

---

### Task 4: Update README

**Files:**
- Modify: `weather_mcp/README.md`

**Step 1: Replace README with weather-specific content**

Replace entire contents with:

```markdown
# weather_mcp MCP Server

An MCP server that provides current weather data using the OpenWeatherMap API.

## Tools

### get_weather

Get current weather for a city.

- **Input:** `city` (string, required) — city name, e.g. "London" or "Tokyo,JP"
- **Output:** Temperature (°C), conditions, humidity (%), wind speed (m/s)

## Setup

1. Get a free API key from [OpenWeatherMap](https://openweathermap.org/api)
2. Set the environment variable: `OPENWEATHER_API_KEY=your_key_here`

## Configuration

### Claude Desktop

On MacOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
On Windows: `%APPDATA%/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "weather_mcp": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/weather_mcp",
        "run",
        "weather-mcp"
      ],
      "env": {
        "OPENWEATHER_API_KEY": "your_key_here"
      }
    }
  }
}
```

## Development

```bash
uv sync
uv run pytest tests/ -v
```

### Debugging

```bash
npx @modelcontextprotocol/inspector uv --directory /path/to/weather_mcp run weather-mcp
```
```

**Step 2: Commit**

```bash
git add weather_mcp/README.md
git commit -m "docs: update README for weather MCP server"
```

---

### Task 5: Manual smoke test

**Step 1: Run with MCP Inspector**

Run: `cd weather_mcp && OPENWEATHER_API_KEY=<your-key> npx @modelcontextprotocol/inspector uv run weather-mcp`

**Step 2: In the Inspector UI:**
- Verify `get_weather` appears in the tools list
- Call `get_weather` with `{"city": "London"}`
- Confirm formatted weather output is returned
