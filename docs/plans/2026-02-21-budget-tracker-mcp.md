# Budget Tracker MCP Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a 4-tool Budget Tracker MCP server (log_expense, set_budget, get_spending_summary, analyze_spending) with local JSON storage.

**Architecture:** Single-module MCP server. Expenses and budgets stored in `expenses.json` next to the server. No external dependencies — uses stdlib `json`, `datetime`, and `pathlib`. The `analyze_spending` tool returns structured data for Claude to provide savings tips.

**Tech Stack:** Python 3.14, MCP SDK (`mcp`), stdlib only

---

### Task 1: Implement server with all 4 tools

**Files:**
- Modify: `budget_tracker_mcp/src/budget_tracker_mcp/server.py` (replace entire contents)
- Modify: `budget_tracker_mcp/src/budget_tracker_mcp/__init__.py`

**Step 1: Update __init__.py**

Replace contents of `budget_tracker_mcp/src/budget_tracker_mcp/__init__.py` with:

```python
from . import server
import asyncio

def main():
    """Main entry point for the package."""
    asyncio.run(server.main())

__all__ = ['main', 'server']
```

**Step 2: Replace server.py**

```python
import json
from datetime import datetime, timedelta
from pathlib import Path

import mcp.server.stdio
import mcp.types as types
from mcp.server import Server

server = Server("budget_tracker_mcp")

DATA_FILE = Path(__file__).parent.parent.parent / "expenses.json"


def _load_data() -> dict:
    if not DATA_FILE.exists():
        return {"expenses": [], "budgets": {}}
    return json.loads(DATA_FILE.read_text())


def _save_data(data: dict) -> None:
    DATA_FILE.write_text(json.dumps(data, indent=2))


def _next_id(expenses: list[dict]) -> str:
    if not expenses:
        return "1"
    return str(max(int(e["id"]) for e in expenses) + 1)


def log_expense(amount: float, category: str, description: str = "") -> str:
    if amount <= 0:
        return "Amount must be positive."

    data = _load_data()
    expense = {
        "id": _next_id(data["expenses"]),
        "amount": round(amount, 2),
        "category": category.lower(),
        "description": description,
        "date": datetime.now().strftime("%Y-%m-%d"),
    }
    data["expenses"].append(expense)
    _save_data(data)

    # Calculate running total for this category this month
    now = datetime.now()
    month_total = sum(
        e["amount"] for e in data["expenses"]
        if e["category"] == category.lower()
        and e["date"][:7] == now.strftime("%Y-%m")
    )

    result = f"Expense #{expense['id']} logged: ${amount:.2f} in {category}"
    if description:
        result += f" ({description})"
    result += f"\nCategory '{category}' total this month: ${month_total:.2f}"

    budget = data["budgets"].get(category.lower())
    if budget:
        remaining = budget - month_total
        if remaining > 0:
            result += f" (${remaining:.2f} remaining of ${budget:.2f} budget)"
        else:
            result += f" (OVER BUDGET by ${abs(remaining):.2f}!)"

    return result


def set_budget(category: str, limit: float) -> str:
    if limit <= 0:
        return "Budget limit must be positive."

    data = _load_data()
    data["budgets"][category.lower()] = round(limit, 2)
    _save_data(data)
    return f"Budget set: ${limit:.2f}/month for '{category}'"


def get_spending_summary(period: str = "month") -> str:
    data = _load_data()
    expenses = data["expenses"]
    budgets = data["budgets"]

    now = datetime.now()
    if period == "week":
        start = (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d")
        filtered = [e for e in expenses if e["date"] >= start]
        period_label = "This Week"
    elif period == "month":
        start = now.strftime("%Y-%m")
        filtered = [e for e in expenses if e["date"][:7] == start]
        period_label = "This Month"
    else:  # all
        filtered = expenses
        period_label = "All Time"

    if not filtered:
        return f"No expenses found for: {period_label}"

    # Group by category
    by_category: dict[str, float] = {}
    for e in filtered:
        by_category[e["category"]] = by_category.get(e["category"], 0) + e["amount"]

    lines = [f"Spending Summary ({period_label}):\n"]
    grand_total = 0.0

    for cat, total in sorted(by_category.items()):
        grand_total += total
        line = f"  {cat}: ${total:.2f}"
        budget = budgets.get(cat)
        if budget:
            remaining = budget - total
            if remaining >= 0:
                line += f" / ${budget:.2f} budget (${remaining:.2f} remaining)"
            else:
                line += f" / ${budget:.2f} budget (OVER by ${abs(remaining):.2f}!)"
        lines.append(line)

    lines.append(f"\n  Total: ${grand_total:.2f}")
    return "\n".join(lines)


def analyze_spending() -> str:
    data = _load_data()
    expenses = data["expenses"]
    budgets = data["budgets"]

    if not expenses:
        return "No expenses recorded yet. Start logging expenses to get spending analysis."

    now = datetime.now()
    month_expenses = [e for e in expenses if e["date"][:7] == now.strftime("%Y-%m")]

    # Build category summaries
    by_category: dict[str, list[dict]] = {}
    for e in month_expenses:
        by_category.setdefault(e["category"], []).append(e)

    lines = [
        "Here is my spending data. Please analyze my habits and suggest personalized savings tips:\n",
        f"Period: {now.strftime('%B %Y')}",
        f"Total expenses this month: {len(month_expenses)}\n",
    ]

    for cat, cat_expenses in sorted(by_category.items()):
        total = sum(e["amount"] for e in cat_expenses)
        budget = budgets.get(cat)
        lines.append(f"  {cat}: ${total:.2f} ({len(cat_expenses)} transactions)")
        if budget:
            pct = (total / budget) * 100
            lines.append(f"    Budget: ${budget:.2f} ({pct:.0f}% used)")
        for e in cat_expenses[-5:]:  # last 5 per category
            desc = f" - {e['description']}" if e["description"] else ""
            lines.append(f"    ${e['amount']:.2f} on {e['date']}{desc}")

    if budgets:
        unspent = [c for c in budgets if c not in by_category]
        if unspent:
            lines.append(f"\n  Categories with budget but no spending: {', '.join(unspent)}")

    lines.append(
        "\nPlease identify spending patterns, flag potential overspending, "
        "and suggest 3-5 specific, actionable savings tips based on this data."
    )
    return "\n".join(lines)


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="log_expense",
            description="Log a new expense",
            inputSchema={
                "type": "object",
                "properties": {
                    "amount": {
                        "type": "number",
                        "description": "Expense amount in dollars",
                    },
                    "category": {
                        "type": "string",
                        "description": "Expense category, e.g. 'food', 'transport', 'entertainment'",
                    },
                    "description": {
                        "type": "string",
                        "description": "Optional description of the expense",
                    },
                },
                "required": ["amount", "category"],
            },
        ),
        types.Tool(
            name="set_budget",
            description="Set a monthly budget limit for a category",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Budget category",
                    },
                    "limit": {
                        "type": "number",
                        "description": "Monthly budget limit in dollars",
                    },
                },
                "required": ["category", "limit"],
            },
        ),
        types.Tool(
            name="get_spending_summary",
            description="Get a spending summary with budget comparison",
            inputSchema={
                "type": "object",
                "properties": {
                    "period": {
                        "type": "string",
                        "enum": ["week", "month", "all"],
                        "description": "Time period for summary (default: month)",
                    },
                },
            },
        ),
        types.Tool(
            name="analyze_spending",
            description="Get spending data formatted for AI-powered savings analysis and tips",
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
        case "log_expense":
            if "amount" not in args or "category" not in args:
                raise ValueError("Missing required arguments: amount and category")
            result = log_expense(args["amount"], args["category"], args.get("description", ""))
        case "set_budget":
            if "category" not in args or "limit" not in args:
                raise ValueError("Missing required arguments: category and limit")
            result = set_budget(args["category"], args["limit"])
        case "get_spending_summary":
            result = get_spending_summary(args.get("period", "month"))
        case "analyze_spending":
            result = analyze_spending()
        case _:
            raise ValueError(f"Unknown tool: {name}")

    return [types.TextContent(type="text", text=result)]


async def main():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())
```

**Step 3: Commit**

```bash
git add budget_tracker_mcp/src/budget_tracker_mcp/
git commit -m "feat(budget): implement log_expense, set_budget, get_spending_summary, analyze_spending"
```

---

### Task 2: Write tests

**Files:**
- Modify: `budget_tracker_mcp/pyproject.toml`
- Create: `budget_tracker_mcp/tests/__init__.py`
- Create: `budget_tracker_mcp/tests/test_server.py`

**Step 1: Add test dependencies**

Add after `[build-system]` in `budget_tracker_mcp/pyproject.toml`:

```toml
[dependency-groups]
dev = [
    "pytest>=8.0",
]
```

Run: `cd budget_tracker_mcp && uv sync`

**Step 2: Create test files**

Create `budget_tracker_mcp/tests/__init__.py` (empty).

Create `budget_tracker_mcp/tests/test_server.py`:

```python
from unittest.mock import patch

from budget_tracker_mcp.server import (
    log_expense,
    set_budget,
    get_spending_summary,
    analyze_spending,
)


def _make_tmp_file(tmp_path):
    return patch("budget_tracker_mcp.server.DATA_FILE", tmp_path / "expenses.json")


def test_log_expense(tmp_path):
    with _make_tmp_file(tmp_path):
        result = log_expense(25.50, "food", "lunch")
    assert "25.50" in result
    assert "food" in result
    assert "lunch" in result


def test_log_expense_negative(tmp_path):
    with _make_tmp_file(tmp_path):
        result = log_expense(-10, "food")
    assert "must be positive" in result


def test_log_expense_with_budget(tmp_path):
    with _make_tmp_file(tmp_path):
        set_budget("food", 100)
        result = log_expense(25, "food")
    assert "remaining" in result
    assert "75.00" in result


def test_log_expense_over_budget(tmp_path):
    with _make_tmp_file(tmp_path):
        set_budget("food", 20)
        result = log_expense(25, "food")
    assert "OVER BUDGET" in result


def test_set_budget(tmp_path):
    with _make_tmp_file(tmp_path):
        result = set_budget("food", 500)
    assert "500.00" in result
    assert "food" in result


def test_set_budget_negative(tmp_path):
    with _make_tmp_file(tmp_path):
        result = set_budget("food", -100)
    assert "must be positive" in result


def test_get_spending_summary_empty(tmp_path):
    with _make_tmp_file(tmp_path):
        result = get_spending_summary("month")
    assert "No expenses found" in result


def test_get_spending_summary_with_data(tmp_path):
    with _make_tmp_file(tmp_path):
        log_expense(30, "food", "groceries")
        log_expense(15, "transport", "bus")
        result = get_spending_summary("month")
    assert "food" in result
    assert "30.00" in result
    assert "transport" in result
    assert "15.00" in result
    assert "Total" in result


def test_get_spending_summary_with_budget(tmp_path):
    with _make_tmp_file(tmp_path):
        set_budget("food", 100)
        log_expense(30, "food")
        result = get_spending_summary("month")
    assert "remaining" in result


def test_get_spending_summary_all(tmp_path):
    with _make_tmp_file(tmp_path):
        log_expense(50, "food")
        result = get_spending_summary("all")
    assert "All Time" in result
    assert "50.00" in result


def test_analyze_spending_empty(tmp_path):
    with _make_tmp_file(tmp_path):
        result = analyze_spending()
    assert "No expenses recorded" in result


def test_analyze_spending_with_data(tmp_path):
    with _make_tmp_file(tmp_path):
        set_budget("food", 200)
        log_expense(30, "food", "groceries")
        log_expense(15, "food", "snack")
        log_expense(50, "entertainment", "movie")
        result = analyze_spending()
    assert "food" in result
    assert "entertainment" in result
    assert "savings tips" in result


def test_category_case_insensitive(tmp_path):
    with _make_tmp_file(tmp_path):
        log_expense(10, "Food")
        log_expense(20, "FOOD")
        result = get_spending_summary("month")
    assert "30.00" in result
```

**Step 3: Run tests**

Run: `cd budget_tracker_mcp && uv run pytest tests/ -v`
Expected: 13 tests PASS

**Step 4: Commit**

```bash
git add budget_tracker_mcp/tests/ budget_tracker_mcp/pyproject.toml budget_tracker_mcp/uv.lock
git commit -m "test(budget): add unit tests for all budget tracker tools"
```

---

### Task 3: Update README and Claude Desktop config

**Files:**
- Modify: `budget_tracker_mcp/README.md`
- Modify: `C:\Users\lzh75\AppData\Roaming\Claude\claude_desktop_config.json`

**Step 1: Replace README**

```markdown
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
```

**Step 2: Add to Claude Desktop config**

Add to mcpServers:

```json
"budget_tracker_mcp": {
  "command": "uv",
  "args": [
    "--directory",
    "D:\\coding\\ai-builder-club\\mcp-lent\\budget_tracker_mcp",
    "run",
    "budget-tracker-mcp"
  ]
}
```

**Step 3: Commit**

```bash
git add budget_tracker_mcp/README.md
git commit -m "docs(budget): update README with tool documentation"
```
