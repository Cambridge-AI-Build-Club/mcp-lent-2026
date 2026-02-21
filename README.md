# MCP Lent 2026

A collection of MCP (Model Context Protocol) servers built during the Cambridge AI Builder Club's Lent 2026 term. Each server gives Claude new capabilities through tools — from checking the weather to managing your budget.

## Servers

| Server | Tools | Description |
|--------|-------|-------------|
| [demo-mcp](demo-mcp/) | `roll_dice`, `flip_coin` | Starter example — build your first MCP server in 10 minutes |
| [weather-mcp](weather-mcp/) | `get_weather` | Current weather for any city via OpenWeatherMap |
| [spotify-mcp](spotify-mcp/) | `get_current_song`, `search_track`, `create_playlist` | Spotify playback info and playlist management |
| [task-manager-mcp](task-manager-mcp/) | `add_task`, `complete_task`, `list_tasks`, `smart_schedule` | Task tracking with AI-powered scheduling |
| [budget-tracker-mcp](budget-tracker-mcp/) | `log_expense`, `set_budget`, `get_spending_summary`, `analyze_spending` | Expense tracking with budget limits and AI analysis |

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- [Claude Desktop](https://claude.ai/download)

## Quick Start

1. Clone the repo:

```bash
git clone https://github.com/Cambridge-AI-Build-Club/mcp-lent-2026.git
cd mcp-lent-2026
```

2. Add a server to your Claude Desktop config (`%APPDATA%/Claude/claude_desktop_config.json` on Windows, `~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "demo-mcp": {
      "command": "uv",
      "args": [
        "--directory",
        "/FULL/PATH/TO/mcp-lent-2026/demo-mcp",
        "run",
        "demo-mcp"
      ]
    }
  }
}
```

3. Restart Claude Desktop and start chatting.

## Environment Variables

Some servers need API keys set in the Claude Desktop config `env` field:

| Server | Variable | Where to get it |
|--------|----------|----------------|
| weather-mcp | `OPENWEATHER_API_KEY` | [openweathermap.org](https://openweathermap.org/api) (free tier) |
| spotify-mcp | `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET` | [developer.spotify.com](https://developer.spotify.com/dashboard) |

## Project Structure

```
mcp-lent-2026/
├── demo-mcp/           # Starter tutorial
├── weather-mcp/        # Weather lookups
├── spotify-mcp/        # Spotify integration
├── task-manager-mcp/   # Task management
├── budget-tracker-mcp/ # Budget tracking
└── docs/plans/         # Design docs
```

Each server follows the same pattern:

```
<server>/
├── pyproject.toml
├── README.md
├── src/<package>/
│   ├── __init__.py
│   └── server.py
└── tests/
```

## Running Tests

```bash
cd budget-tracker-mcp
uv run pytest

cd ../task-manager-mcp
uv run pytest
```
