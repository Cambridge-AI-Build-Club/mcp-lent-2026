# budget_tracker_mcp MCP Server

An MCP server for tracking expenses, managing budgets, and getting AI-powered savings tips.

## Tools

### log_expense

Log a new expense.

- **Input:** `amount` (number, required), `category` (string, required), `description` (string, optional)
- **Output:** Confirmation with running category total and budget status

### set_budget

Set a monthly budget limit for a category.

- **Input:** `category` (string, required), `limit` (number, required)
- **Output:** Budget set confirmation

### get_spending_summary

Get spending breakdown by category.

- **Input:** `period` (week/month/all, default: month)
- **Output:** Category totals with budget comparison

### analyze_spending

Get spending data formatted for AI analysis.

- **Input:** none
- **Output:** Structured spending data for Claude to provide personalized savings tips

## Configuration

### Claude Desktop

On MacOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
On Windows: `%APPDATA%/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "budget_tracker_mcp": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/budget_tracker_mcp",
        "run",
        "budget-tracker-mcp"
      ]
    }
  }
}
```

Expenses are stored in `expenses.json` in the project directory.

## Development

```bash
uv sync
uv run pytest tests/ -v
```
