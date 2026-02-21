import json
from datetime import datetime
from pathlib import Path

import mcp.server.stdio
import mcp.types as types
from mcp.server import Server

server = Server("task_manager_mcp")

TASKS_FILE = Path(__file__).parent.parent.parent / "tasks.json"


def _load_tasks() -> list[dict]:
    if not TASKS_FILE.exists():
        return []
    data = json.loads(TASKS_FILE.read_text())
    return data.get("tasks", [])


def _save_tasks(tasks: list[dict]) -> None:
    TASKS_FILE.write_text(json.dumps({"tasks": tasks}, indent=2))


def _next_id(tasks: list[dict]) -> str:
    if not tasks:
        return "1"
    return str(max(int(t["id"]) for t in tasks) + 1)


def add_task(title: str, priority: str = "medium") -> str:
    if priority not in ("low", "medium", "high"):
        return f"Invalid priority: {priority}. Must be low, medium, or high."

    tasks = _load_tasks()
    task = {
        "id": _next_id(tasks),
        "title": title,
        "status": "pending",
        "priority": priority,
        "created_at": datetime.now().isoformat(),
    }
    tasks.append(task)
    _save_tasks(tasks)
    return f"Task #{task['id']} created: {title} (priority: {priority})"


def complete_task(task_id: str) -> str:
    tasks = _load_tasks()
    for task in tasks:
        if task["id"] == task_id:
            if task["status"] == "completed":
                return f"Task #{task_id} is already completed."
            task["status"] = "completed"
            _save_tasks(tasks)
            return f"Task #{task_id} completed: {task['title']}"
    return f"Task #{task_id} not found."


def list_tasks(filter_status: str = "all", priority: str | None = None) -> str:
    tasks = _load_tasks()

    if not tasks:
        return "No tasks found."

    if filter_status != "all":
        tasks = [t for t in tasks if t["status"] == filter_status]

    if priority:
        tasks = [t for t in tasks if t["priority"] == priority]

    if not tasks:
        return "No tasks match the filter."

    lines = []
    for t in tasks:
        status_icon = "[x]" if t["status"] == "completed" else "[ ]"
        lines.append(
            f"  {status_icon} #{t['id']} {t['title']} "
            f"(priority: {t['priority']}, created: {t['created_at'][:10]})"
        )
    return f"Tasks ({len(lines)}):\n" + "\n".join(lines)


def smart_schedule() -> str:
    tasks = _load_tasks()
    pending = [t for t in tasks if t["status"] == "pending"]

    if not pending:
        return "No pending tasks to schedule."

    lines = ["Here are all pending tasks. Please analyze them and suggest a prioritized order:\n"]
    for t in pending:
        created = datetime.fromisoformat(t["created_at"])
        age_days = (datetime.now() - created).days
        lines.append(
            f"  - #{t['id']} \"{t['title']}\" "
            f"(priority: {t['priority']}, age: {age_days} day(s))"
        )

    lines.append(
        "\nConsider priority level, task age, and any logical dependencies "
        "you can infer from the task titles."
    )
    return "\n".join(lines)


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="add_task",
            description="Add a new task to your task list",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "The task title",
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                        "description": "Task priority (default: medium)",
                    },
                },
                "required": ["title"],
            },
        ),
        types.Tool(
            name="complete_task",
            description="Mark a task as completed",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "The ID of the task to complete",
                    },
                },
                "required": ["task_id"],
            },
        ),
        types.Tool(
            name="list_tasks",
            description="List tasks with optional filters",
            inputSchema={
                "type": "object",
                "properties": {
                    "filter": {
                        "type": "string",
                        "enum": ["all", "pending", "completed"],
                        "description": "Filter by status (default: all)",
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                        "description": "Filter by priority",
                    },
                },
            },
        ),
        types.Tool(
            name="smart_schedule",
            description="Get all pending tasks formatted for AI-powered prioritization",
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
    args = arguments or {}

    match name:
        case "add_task":
            if "title" not in args:
                raise ValueError("Missing required argument: title")
            result = add_task(args["title"], args.get("priority", "medium"))
        case "complete_task":
            if "task_id" not in args:
                raise ValueError("Missing required argument: task_id")
            result = complete_task(args["task_id"])
        case "list_tasks":
            result = list_tasks(args.get("filter", "all"), args.get("priority"))
        case "smart_schedule":
            result = smart_schedule()
        case _:
            raise ValueError(f"Unknown tool: {name}")

    return [types.TextContent(type="text", text=result)]


async def main():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())
