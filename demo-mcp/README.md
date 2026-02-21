# Build Your First MCP Server in 10 Minutes

A dice roller MCP server — the simplest possible example to learn the MCP pattern.

## What You'll Build

| Tool | What it does |
|------|-------------|
| `roll_dice` | Roll a dice with any number of sides |
| `flip_coin` | Flip a coin — heads or tails |

## Prerequisites

- Python 3.12+ installed
- [uv](https://docs.astral.sh/uv/getting-started/installation/) installed
- Claude Desktop installed

## Step-by-Step Guide

### Step 1: Create the project (2 min)

```bash
uv init --package --name demo-mcp demo_mcp
cd demo_mcp
uv add mcp
```

### Step 2: Write the server (5 min)

Open `src/demo_mcp/server.py` and replace everything with:

```python
import random

import mcp.server.stdio
import mcp.types as types
from mcp.server import Server

server = Server("demo_mcp")


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="roll_dice",
            description="Roll a dice with the specified number of sides",
            inputSchema={
                "type": "object",
                "properties": {
                    "sides": {
                        "type": "integer",
                        "description": "Number of sides (default: 6)",
                    },
                },
            },
        ),
        types.Tool(
            name="flip_coin",
            description="Flip a coin",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent]:
    match name:
        case "roll_dice":
            sides = (arguments or {}).get("sides", 6)
            result = random.randint(1, sides)
            text = f"Rolled a {result} (d{sides})"
        case "flip_coin":
            text = random.choice(["Heads!", "Tails!"])
        case _:
            raise ValueError(f"Unknown tool: {name}")

    return [types.TextContent(type="text", text=text)]


async def main():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())
```

Then open `src/demo_mcp/__init__.py` and replace with:

```python
from . import server
import asyncio

def main():
    asyncio.run(server.main())
```

### Step 3: Add to Claude Desktop (2 min)

Open your Claude Desktop config:

- **MacOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%/Claude/claude_desktop_config.json`

Add this to the `mcpServers` section:

```json
{
  "mcpServers": {
    "demo_mcp": {
      "command": "uv",
      "args": [
        "--directory",
        "/FULL/PATH/TO/demo_mcp",
        "run",
        "demo-mcp"
      ]
    }
  }
}
```

Replace `/FULL/PATH/TO/demo_mcp` with the actual path to your project.

### Step 4: Test it! (1 min)

Restart Claude Desktop, then try:

- "Roll a d20"
- "Flip a coin"
- "Roll 3 dice and tell me the total"
- "We're playing D&D — roll for initiative!"

## How It Works

```
You (in Claude Desktop)          Claude              Your MCP Server
        |                          |                       |
        |  "Roll a d20"           |                       |
        |------------------------->|                       |
        |                          |  call: roll_dice(20) |
        |                          |---------------------->|
        |                          |                       | random.randint(1,20)
        |                          |  "Rolled a 17 (d20)" |
        |                          |<----------------------|
        |  "You rolled a 17!"     |                       |
        |<-------------------------|                       |
```

## Key Concepts

1. **`@server.list_tools()`** — Tell Claude what tools are available and their input schemas
2. **`@server.call_tool()`** — Handle the actual tool calls and return results
3. **`types.TextContent`** — All results are returned as text for Claude to interpret
4. **Claude Desktop config** — Tells Claude how to start your server

That's it! You've built an MCP server. Now go build something useful.
