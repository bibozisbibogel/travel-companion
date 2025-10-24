"""Hooks for Claude Agent SDK tool execution monitoring and validation."""

import logging
from decimal import Decimal
from typing import Any

logger = logging.getLogger(__name__)


class BudgetTracker:
    """Track budget allocation and spending across tool executions."""

    def __init__(self, total_budget: Decimal, currency: str = "USD") -> None:
        """
        Initialize budget tracker.

        Args:
            total_budget: Total trip budget
            currency: Currency code
        """
        self.total_budget = total_budget
        self.currency = currency
        self.allocated = Decimal("0")
        self.spent = Decimal("0")

        # Budget allocations by category
        self.allocations = {
            "flights": Decimal("0"),
            "hotels": Decimal("0"),
            "activities": Decimal("0"),
            "food": Decimal("0"),
        }

        logger.info(f"Budget tracker initialized: {total_budget} {currency}")

    def allocate(self, category: str, amount: Decimal) -> bool:
        """
        Allocate budget to a category.

        Args:
            category: Budget category (flights, hotels, activities, food)
            amount: Amount to allocate

        Returns:
            True if allocation successful, False if exceeds budget
        """
        if category not in self.allocations:
            logger.warning(f"Unknown budget category: {category}")
            return False

        new_allocated = self.allocated + amount

        if new_allocated > self.total_budget:
            logger.warning(
                f"Budget allocation would exceed total: {new_allocated} > {self.total_budget}"
            )
            return False

        self.allocations[category] += amount
        self.allocated = new_allocated

        logger.info(
            f"Allocated {amount} {self.currency} to {category}. "
            f"Total allocated: {self.allocated}/{self.total_budget}"
        )

        return True

    def spend(self, category: str, amount: Decimal) -> bool:
        """
        Record spending in a category.

        Args:
            category: Budget category
            amount: Amount spent

        Returns:
            True if spending recorded, False if exceeds allocation
        """
        if category not in self.allocations:
            logger.warning(f"Unknown budget category: {category}")
            return False

        if amount > self.allocations[category]:
            logger.warning(
                f"Spending {amount} exceeds allocation {self.allocations[category]} for {category}"
            )
            return False

        self.spent += amount
        logger.info(
            f"Recorded spending: {amount} {self.currency} in {category}. "
            f"Total spent: {self.spent}/{self.allocated}"
        )

        return True

    def get_remaining(self) -> Decimal:
        """Get remaining budget."""
        return self.total_budget - self.allocated

    def get_summary(self) -> dict[str, Any]:
        """Get budget summary."""
        return {
            "total_budget": float(self.total_budget),
            "currency": self.currency,
            "allocated": float(self.allocated),
            "spent": float(self.spent),
            "remaining": float(self.get_remaining()),
            "allocations": {k: float(v) for k, v in self.allocations.items()},
            "utilization_percent": float((self.allocated / self.total_budget) * 100),
        }


async def pre_tool_use_hook(
    tool_name: str, tool_input: dict[str, Any], context: dict[str, Any]
) -> dict[str, Any]:
    """
    Hook executed before tool use for validation and logging.

    Args:
        tool_name: Name of the tool about to be executed
        tool_input: Input arguments for the tool
        context: Execution context with budget tracker and other metadata

    Returns:
        Hook result with permission decision and optional modifications
    """
    logger.info(f"Pre-tool hook: {tool_name} with input: {tool_input}")

    # Extract budget tracker from context
    budget_tracker = context.get("budget_tracker")

    # Validate budget constraints for cost-related tools
    if budget_tracker and tool_name in [
        "search_flights",
        "search_hotels",
        "search_activities",
        "search_restaurants",
    ]:
        # Map tools to budget categories
        category_map = {
            "search_flights": "flights",
            "search_hotels": "hotels",
            "search_activities": "activities",
            "search_restaurants": "food",
        }

        category = category_map.get(tool_name)

        if category:
            # Check if there's budget remaining for this category
            remaining = budget_tracker.get_remaining()

            if remaining <= Decimal("0"):
                logger.warning(f"Budget exhausted, denying {tool_name}")
                return {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": "Budget exhausted",
                    }
                }

            # Add budget filter to tool input if not present
            budget_fields = {
                "search_flights": "max_price",
                "search_hotels": "budget_per_night",
                "search_activities": "budget_per_activity",
                "search_restaurants": "budget_per_person",
            }

            budget_field = budget_fields.get(tool_name)
            if budget_field and budget_field not in tool_input:
                # Estimate reasonable per-item budget
                per_item_budget = remaining / Decimal("2")  # Conservative estimate
                tool_input[budget_field] = float(per_item_budget)
                logger.info(
                    f"Added budget constraint to {tool_name}: {budget_field}={per_item_budget}"
                )

    # Validate required fields
    required_fields_map = {
        "search_flights": ["origin", "destination", "departure_date"],
        "search_hotels": ["location", "check_in_date", "check_out_date", "guest_count"],
        "search_activities": ["location", "date"],
        "search_restaurants": ["location", "date"],
    }

    if tool_name in required_fields_map:
        required = required_fields_map[tool_name]
        missing = [f for f in required if f not in tool_input or not tool_input[f]]

        if missing:
            logger.warning(f"Missing required fields for {tool_name}: {missing}")
            return {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": f"Missing required fields: {', '.join(missing)}",
                }
            }

    # Allow execution
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
        }
    }


async def post_tool_use_hook(
    tool_name: str,
    tool_input: dict[str, Any],
    tool_result: Any,
    context: dict[str, Any],
) -> dict[str, Any]:
    """
    Hook executed after tool use for logging and budget updates.

    Args:
        tool_name: Name of the executed tool
        tool_input: Input arguments used
        tool_result: Result from tool execution
        context: Execution context with budget tracker

    Returns:
        Hook result with metadata
    """
    logger.info(f"Post-tool hook: {tool_name} completed")

    budget_tracker = context.get("budget_tracker")

    # Parse result and update budget allocations
    if budget_tracker and isinstance(tool_result, dict):
        category_map = {
            "search_flights": "flights",
            "search_hotels": "hotels",
            "search_activities": "activities",
            "search_restaurants": "food",
        }

        category = category_map.get(tool_name)

        if category and "content" in tool_result:
            # Extract pricing information from results
            import json

            try:
                content_text = tool_result["content"][0]["text"]
                result_data = json.loads(content_text)

                # Calculate estimated cost based on results
                if tool_name == "search_flights" and "flights" in result_data:
                    flights = result_data["flights"]
                    if flights:
                        # Use cheapest flight as estimate
                        min_price = min(f["price"] for f in flights)
                        budget_tracker.allocate(category, Decimal(str(min_price)))

                elif tool_name == "search_hotels" and "hotels" in result_data:
                    hotels = result_data["hotels"]
                    if hotels and "nights" in result_data:
                        # Use cheapest hotel total price
                        min_total = min(h["total_price"] for h in hotels)
                        budget_tracker.allocate(category, Decimal(str(min_total)))

                elif tool_name == "search_activities" and "activities" in result_data:
                    activities = result_data["activities"]
                    if activities:
                        # Estimate cost for 3 activities
                        avg_price = sum(a["price"] for a in activities[:3]) / len(activities[:3])
                        estimated_total = avg_price * 3
                        budget_tracker.allocate(category, Decimal(str(estimated_total)))

                elif tool_name == "search_restaurants" and "restaurants" in result_data:
                    restaurants = result_data["restaurants"]
                    if restaurants:
                        # Estimate food cost (3 meals/day for trip duration)
                        avg_cost = sum(
                            r["average_cost_per_person"]
                            for r in restaurants[:3]
                            if r.get("average_cost_per_person")
                        ) / len([r for r in restaurants[:3] if r.get("average_cost_per_person")])
                        # Assume 3 days worth of meals
                        estimated_total = avg_cost * 3 * 3
                        budget_tracker.allocate(category, Decimal(str(estimated_total)))

            except (json.JSONDecodeError, KeyError, ValueError, ZeroDivisionError) as e:
                logger.warning(f"Could not parse tool result for budget tracking: {e}")

    return {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "metadata": {
                "tool": tool_name,
                "success": True,
                "budget_summary": (budget_tracker.get_summary() if budget_tracker else None),
            },
        }
    }
