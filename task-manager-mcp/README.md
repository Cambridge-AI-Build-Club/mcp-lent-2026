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
