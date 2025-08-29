"""Simple demonstration workflow implementation."""

from typing import Any

from .nodes import WorkflowNodes
from .orchestrator import BaseWorkflow


class TravelPlanningWorkflow(BaseWorkflow):
    """
    Simple travel planning workflow for demonstration purposes.

    Implements a basic 3-node workflow:
    start -> process -> end

    This serves as a foundation for more complex travel planning workflows.
    """

    def __init__(self) -> None:
        """Initialize the travel planning workflow."""
        super().__init__("TravelPlanningWorkflow")

    def define_nodes(self) -> dict[str, Any]:
        """
        Define workflow nodes.

        Returns:
            Dictionary mapping node names to callable functions
        """
        return {
            "start": WorkflowNodes.start_node,
            "process": WorkflowNodes.process_node,
            "end": WorkflowNodes.end_node,
        }

    def define_edges(self) -> list[tuple[str, str]]:
        """
        Define workflow edges and transitions.

        Creates a simple linear workflow: start -> process -> end

        Returns:
            List of tuples defining graph edges
        """
        return [
            ("start", "process"),
            ("process", "end"),
        ]

    def get_entry_point(self) -> str:
        """
        Get the workflow entry point node name.

        Returns:
            Name of the starting node
        """
        return "start"
