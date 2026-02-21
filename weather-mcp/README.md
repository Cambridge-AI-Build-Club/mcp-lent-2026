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
