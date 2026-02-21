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
    else:
        filtered = expenses
        period_label = "All Time"

    if not filtered:
        return f"No expenses found for: {period_label}"

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
        for e in cat_expenses[-5:]:
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
