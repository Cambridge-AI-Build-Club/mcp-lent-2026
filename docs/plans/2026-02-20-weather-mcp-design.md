# Weather MCP Server Design

## Overview

Replace the template notes MCP server with a single-tool weather server that calls OpenWeatherMap's Current Weather API.

## Tool

- **Name:** `get_weather`
- **Input:** `{ "city": string }` (required) — city name, e.g. "London" or "Tokyo,JP"
- **Output:** Formatted text with temperature (C), description, humidity (%), wind speed (m/s)

## Data Flow

1. MCP client calls `get_weather` with a city name
2. Server reads `OPENWEATHER_API_KEY` from environment
3. `httpx.AsyncClient` calls `https://api.openweathermap.org/data/2.5/weather?q={city}&appid={key}&units=metric`
4. Parse JSON response, extract relevant fields
5. Return formatted text to the MCP client

## Error Handling

- Missing API key: return clear error message
- City not found (404): return "City not found" message
- Network/API errors: return error message with status code

## Files Changed

- `server.py` — replace all template code with weather implementation
- `pyproject.toml` — add `httpx` dependency
- `README.md` — update to reflect weather tool

## Decisions

- **HTTP client:** httpx (async-native, clean API)
- **API key config:** environment variable `OPENWEATHER_API_KEY`
- **Units:** metric (Celsius, m/s)
- **Scope:** single tool only, no resources or prompts
