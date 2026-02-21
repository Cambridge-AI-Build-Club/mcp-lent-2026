# Budget Tracker MCP Server Design

## Overview

Single-module MCP server with 4 tools for expense tracking and budget management. Data stored in local expenses.json file. No external dependencies.

## Tools

| Tool | Input | Output |
|------|-------|--------|
| log_expense | amount (number), category (string), optional description | Confirmation with running category total |
| set_budget | category (string), limit (number) | Budget set confirmation |
| get_spending_summary | period (week/month/all, default: month) | Breakdown by category with budget vs actual |
| analyze_spending | none | All data formatted for LLM savings tips |

## Data Schema

- expenses: list of {id, amount, category, description, date}
- budgets: dict of {category: limit}
- Storage: expenses.json in project directory
- Auto-created if missing

## analyze_spending

Returns all expenses and budgets as structured text for Claude to analyze patterns, identify overspending, and suggest savings tips. Server provides data; LLM reasons.

## Error Handling

- Negative amount: "Amount must be positive"
- Empty file: auto-create
- No expenses in period: "No expenses found"

## Files

- server.py — 4 tools + JSON helpers
- pyproject.toml — mcp only
- README.md — usage docs
