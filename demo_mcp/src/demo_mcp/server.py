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
