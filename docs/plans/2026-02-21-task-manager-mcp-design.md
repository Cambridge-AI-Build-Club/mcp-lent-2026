# Task Manager MCP Server Design

## Overview

Single-module MCP server with 4 tools for task management. Tasks stored in local tasks.json file. No external dependencies beyond MCP SDK.

## Tools

| Tool | Input | Output |
|------|-------|--------|
| add_task | title, optional priority (low/medium/high, default medium) | Created task with ID |
| complete_task | task_id | Completion confirmation |
| list_tasks | optional filter (all/pending/completed), optional priority | Formatted task list |
| smart_schedule | none | Pending tasks as structured text for LLM prioritization |

## Task Schema

- id: auto-incrementing string
- title: string
- status: "pending" or "completed"
- priority: "low", "medium", or "high"
- created_at: ISO 8601 datetime string

## Storage

- File: tasks.json in the task_manager_mcp project directory
- Format: { "tasks": [...] }
- Auto-created if missing

## smart_schedule

Returns all pending tasks with priorities and ages as structured text. The server provides data; the LLM client reasons about prioritization.

## Error Handling

- Task not found: "Task {id} not found"
- Empty list: "No tasks found"
- Missing file: auto-create empty

## Files

- server.py — 4 tools + JSON helpers
- pyproject.toml — mcp dependency only
- README.md — usage docs
