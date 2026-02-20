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
