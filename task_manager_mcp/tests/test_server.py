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
