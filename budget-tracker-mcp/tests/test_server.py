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
