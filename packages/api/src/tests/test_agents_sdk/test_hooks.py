"""Tests for Claude Agent SDK hooks (budget tracking, validation, logging)."""

from decimal import Decimal

import pytest


def test_budget_tracker_initialization():
    """Test budget tracker initialization."""
    from travel_companion.agents_sdk.hooks import BudgetTracker

    tracker = BudgetTracker(total_budget=Decimal("5000"), currency="USD")

    assert tracker.total_budget == Decimal("5000")
    assert tracker.currency == "USD"
    assert tracker.allocated == Decimal("0")
    assert tracker.spent == Decimal("0")
    assert tracker.get_remaining() == Decimal("5000")


def test_budget_tracker_allocation():
    """Test budget allocation to categories."""
    from travel_companion.agents_sdk.hooks import BudgetTracker

    tracker = BudgetTracker(total_budget=Decimal("5000"), currency="USD")

    # Allocate to flights
    assert tracker.allocate("flights", Decimal("1200")) is True
    assert tracker.allocated == Decimal("1200")
    assert tracker.allocations["flights"] == Decimal("1200")
    assert tracker.get_remaining() == Decimal("3800")

    # Allocate to hotels
    assert tracker.allocate("hotels", Decimal("1500")) is True
    assert tracker.allocated == Decimal("2700")
    assert tracker.allocations["hotels"] == Decimal("1500")
    assert tracker.get_remaining() == Decimal("2300")


def test_budget_tracker_over_allocation():
    """Test that over-allocation is prevented."""
    from travel_companion.agents_sdk.hooks import BudgetTracker

    tracker = BudgetTracker(total_budget=Decimal("1000"), currency="USD")

    # Try to allocate more than budget
    assert tracker.allocate("flights", Decimal("1200")) is False
    assert tracker.allocated == Decimal("0")  # Should not be allocated


def test_budget_tracker_spending():
    """Test recording spending against allocations."""
    from travel_companion.agents_sdk.hooks import BudgetTracker

    tracker = BudgetTracker(total_budget=Decimal("5000"), currency="USD")

    # Allocate and spend
    tracker.allocate("flights", Decimal("1200"))
    assert tracker.spend("flights", Decimal("1150")) is True
    assert tracker.spent == Decimal("1150")


def test_budget_tracker_overspending():
    """Test that overspending is prevented."""
    from travel_companion.agents_sdk.hooks import BudgetTracker

    tracker = BudgetTracker(total_budget=Decimal("5000"), currency="USD")

    # Allocate less than spending attempt
    tracker.allocate("flights", Decimal("500"))
    assert tracker.spend("flights", Decimal("600")) is False
    assert tracker.spent == Decimal("0")  # Should not be recorded


def test_budget_tracker_summary():
    """Test budget summary generation."""
    from travel_companion.agents_sdk.hooks import BudgetTracker

    tracker = BudgetTracker(total_budget=Decimal("5000"), currency="USD")

    tracker.allocate("flights", Decimal("1200"))
    tracker.allocate("hotels", Decimal("1800"))
    tracker.spend("flights", Decimal("1150"))

    summary = tracker.get_summary()

    assert summary["total_budget"] == 5000.0
    assert summary["currency"] == "USD"
    assert summary["allocated"] == 3000.0
    assert summary["spent"] == 1150.0
    assert summary["remaining"] == 2000.0
    assert summary["utilization_percent"] == 60.0
    assert summary["allocations"]["flights"] == 1200.0
    assert summary["allocations"]["hotels"] == 1800.0


@pytest.mark.asyncio
async def test_pre_tool_use_hook_budget_validation():
    """Test pre-tool hook validates budget constraints."""
    from travel_companion.agents_sdk.hooks import BudgetTracker, pre_tool_use_hook

    # Create budget tracker with limited budget
    tracker = BudgetTracker(total_budget=Decimal("100"), currency="USD")
    tracker.allocate("flights", Decimal("100"))  # Fully allocate budget

    context = {"budget_tracker": tracker}

    # Try to use search_flights tool with no remaining budget
    result = await pre_tool_use_hook(
        tool_name="search_flights",
        tool_input={"origin": "JFK", "destination": "LAX", "departure_date": "2025-06-01"},
        context=context,
    )

    # Should deny due to budget exhaustion
    assert result["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "Budget exhausted" in result["hookSpecificOutput"]["permissionDecisionReason"]


@pytest.mark.asyncio
async def test_pre_tool_use_hook_missing_fields():
    """Test pre-tool hook validates required fields."""
    from travel_companion.agents_sdk.hooks import pre_tool_use_hook

    # Missing required field (destination)
    result = await pre_tool_use_hook(
        tool_name="search_flights",
        tool_input={"origin": "JFK", "departure_date": "2025-06-01"},
        context={},
    )

    # Should deny due to missing fields
    assert result["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "Missing required fields" in result["hookSpecificOutput"]["permissionDecisionReason"]


@pytest.mark.asyncio
async def test_pre_tool_use_hook_allow():
    """Test pre-tool hook allows valid requests."""
    from travel_companion.agents_sdk.hooks import BudgetTracker, pre_tool_use_hook

    tracker = BudgetTracker(total_budget=Decimal("5000"), currency="USD")
    context = {"budget_tracker": tracker}

    result = await pre_tool_use_hook(
        tool_name="search_flights",
        tool_input={
            "origin": "JFK",
            "destination": "LAX",
            "departure_date": "2025-06-01",
        },
        context=context,
    )

    # Should allow
    assert result["hookSpecificOutput"]["permissionDecision"] == "allow"


@pytest.mark.asyncio
async def test_post_tool_use_hook_logging():
    """Test post-tool hook logs tool execution."""
    from travel_companion.agents_sdk.hooks import post_tool_use_hook

    result = await post_tool_use_hook(
        tool_name="search_flights",
        tool_input={"origin": "JFK", "destination": "LAX"},
        tool_result={"content": [{"type": "text", "text": '{"status": "success"}'}]},
        context={},
    )

    # Should return metadata
    assert "hookSpecificOutput" in result
    assert result["hookSpecificOutput"]["hookEventName"] == "PostToolUse"
    assert result["hookSpecificOutput"]["metadata"]["tool"] == "search_flights"
    assert result["hookSpecificOutput"]["metadata"]["success"] is True
