# Task Manager MCP Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a 4-tool Task Manager MCP server (add_task, complete_task, list_tasks, smart_schedule) with local JSON file storage.

**Architecture:** Single-module MCP server. Tasks stored in `tasks.json` next to the server. No external dependencies — uses stdlib `json`, `datetime`, and `pathlib` for file I/O. The `smart_schedule` tool returns structured task data for Claude to reason about.

**Tech Stack:** Python 3.14, MCP SDK (`mcp`), stdlib only

---

### Task 1: Implement server with all 4 tools

**Files:**
- Modify: `task_manager_mcp/src/task_manager_mcp/server.py` (replace entire contents)

**Step 1: Replace server.py**

```python
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
```

**Step 2: Commit**

```bash
git add task_manager_mcp/src/task_manager_mcp/server.py
git commit -m "feat(tasks): implement add_task, complete_task, list_tasks, smart_schedule tools"
```

---

### Task 2: Write tests

**Files:**
- Modify: `task_manager_mcp/pyproject.toml`
- Create: `task_manager_mcp/tests/__init__.py`
- Create: `task_manager_mcp/tests/test_server.py`

**Step 1: Add test dependencies**

Add after `[build-system]` in `task_manager_mcp/pyproject.toml`:

```toml
[dependency-groups]
dev = [
    "pytest>=8.0",
]
```

Run: `cd task_manager_mcp && uv sync`

**Step 2: Create test files**

Create `task_manager_mcp/tests/__init__.py` (empty).

Create `task_manager_mcp/tests/test_server.py`:

```python
import json
from unittest.mock import patch
from pathlib import Path

from task_manager_mcp.server import (
    add_task,
    complete_task,
    list_tasks,
    smart_schedule,
    _load_tasks,
    _save_tasks,
)


def _make_tmp_file(tmp_path):
    """Return a patch context that redirects TASKS_FILE to a temp file."""
    return patch("task_manager_mcp.server.TASKS_FILE", tmp_path / "tasks.json")


def test_add_task(tmp_path):
    with _make_tmp_file(tmp_path):
        result = add_task("Buy groceries", "high")
    assert "Task #1 created" in result
    assert "Buy groceries" in result
    assert "high" in result


def test_add_task_default_priority(tmp_path):
    with _make_tmp_file(tmp_path):
        result = add_task("Read a book")
    assert "medium" in result


def test_add_task_invalid_priority(tmp_path):
    with _make_tmp_file(tmp_path):
        result = add_task("Bad task", "urgent")
    assert "Invalid priority" in result


def test_complete_task(tmp_path):
    with _make_tmp_file(tmp_path):
        add_task("Do laundry")
        result = complete_task("1")
    assert "completed" in result
    assert "Do laundry" in result


def test_complete_task_not_found(tmp_path):
    with _make_tmp_file(tmp_path):
        result = complete_task("999")
    assert "not found" in result


def test_complete_task_already_completed(tmp_path):
    with _make_tmp_file(tmp_path):
        add_task("Already done")
        complete_task("1")
        result = complete_task("1")
    assert "already completed" in result


def test_list_tasks_empty(tmp_path):
    with _make_tmp_file(tmp_path):
        result = list_tasks()
    assert "No tasks found" in result


def test_list_tasks_with_filter(tmp_path):
    with _make_tmp_file(tmp_path):
        add_task("Task A", "high")
        add_task("Task B", "low")
        complete_task("1")
        result = list_tasks("pending")
    assert "Task B" in result
    assert "Task A" not in result


def test_list_tasks_with_priority_filter(tmp_path):
    with _make_tmp_file(tmp_path):
        add_task("High task", "high")
        add_task("Low task", "low")
        result = list_tasks("all", "high")
    assert "High task" in result
    assert "Low task" not in result


def test_smart_schedule(tmp_path):
    with _make_tmp_file(tmp_path):
        add_task("Important thing", "high")
        add_task("Minor thing", "low")
        result = smart_schedule()
    assert "Important thing" in result
    assert "Minor thing" in result
    assert "prioritized order" in result


def test_smart_schedule_empty(tmp_path):
    with _make_tmp_file(tmp_path):
        result = smart_schedule()
    assert "No pending tasks" in result


def test_auto_increment_ids(tmp_path):
    with _make_tmp_file(tmp_path):
        add_task("First")
        add_task("Second")
        add_task("Third")
        result = list_tasks()
    assert "#1" in result
    assert "#2" in result
    assert "#3" in result
```

**Step 3: Run tests**

Run: `cd task_manager_mcp && uv run pytest tests/ -v`
Expected: 12 tests PASS

**Step 4: Commit**

```bash
git add task_manager_mcp/tests/ task_manager_mcp/pyproject.toml task_manager_mcp/uv.lock
git commit -m "test(tasks): add unit tests for all task manager tools"
```

---

### Task 3: Update README

**Files:**
- Modify: `task_manager_mcp/README.md`

**Step 1: Replace README**

```markdown
# task_manager_mcp MCP Server

An MCP server for managing tasks with local JSON storage and AI-powered prioritization.

## Tools

### add_task

Add a new task.

- **Input:** `title` (string, required), `priority` (low/medium/high, default: medium)
- **Output:** Confirmation with task ID

### complete_task

Mark a task as completed.

- **Input:** `task_id` (string, required)
- **Output:** Completion confirmation

### list_tasks

List tasks with optional filters.

- **Input:** `filter` (all/pending/completed, default: all), `priority` (low/medium/high)
- **Output:** Formatted task list

### smart_schedule

Get pending tasks formatted for AI prioritization.

- **Input:** none
- **Output:** Structured task summary for Claude to analyze and suggest a prioritized order

## Configuration

### Claude Desktop

On MacOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
On Windows: `%APPDATA%/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "task_manager_mcp": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/task_manager_mcp",
        "run",
        "task-manager-mcp"
      ]
    }
  }
}
```

Tasks are stored in `tasks.json` in the project directory.

## Development

```bash
uv sync
uv run pytest tests/ -v
```
```

**Step 2: Commit**

```bash
git add task_manager_mcp/README.md
git commit -m "docs(tasks): update README with tool documentation"
```

---

### Task 4: Update Claude Desktop config

**Files:**
- Modify: `C:\Users\lzh75\AppData\Roaming\Claude\claude_desktop_config.json`

**Step 1: Add task_manager_mcp entry**

Add to the mcpServers object:

```json
"task_manager_mcp": {
  "command": "uv",
  "args": [
    "--directory",
    "D:\\coding\\ai-builder-club\\mcp-lent\\task_manager_mcp",
    "run",
    "task-manager-mcp"
  ]
}
```

**Step 2: Restart Claude Desktop and test**

- Try: "Add a task to buy groceries with high priority"
- Try: "List all my tasks"
- Try: "Smart schedule my tasks"
