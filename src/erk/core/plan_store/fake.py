"""In-memory fake implementation for plan storage."""

from pathlib import Path

from erk.core.plan_store.store import PlanStore
from erk.core.plan_store.types import Plan, PlanQuery


class FakePlanStore(PlanStore):
    """In-memory fake implementation for testing.

    All state is provided via constructor. Supports filtering by state,
    labels (AND logic), and limit.
    """

    def __init__(self, plans: dict[str, Plan] | None = None) -> None:
        """Create FakePlanStore with pre-configured state.

        Args:
            plans: Mapping of plan_identifier -> Plan
        """
        self._plans = plans or {}

    def get_plan(self, repo_root: Path, plan_identifier: str) -> Plan:
        """Get plan from fake storage.

        Args:
            repo_root: Repository root directory (ignored in fake)
            plan_identifier: Plan identifier

        Returns:
            Plan from fake storage

        Raises:
            RuntimeError: If plan identifier not found (simulates provider error)
        """
        if plan_identifier not in self._plans:
            msg = f"Plan '{plan_identifier}' not found"
            raise RuntimeError(msg)
        return self._plans[plan_identifier]

    def list_plans(self, repo_root: Path, query: PlanQuery) -> list[Plan]:
        """Query plans from fake storage.

        Args:
            repo_root: Repository root directory (ignored in fake)
            query: Filter criteria (labels, state, limit)

        Returns:
            List of Plan matching the criteria
        """
        plans = list(self._plans.values())

        # Filter by state
        if query.state:
            plans = [plan for plan in plans if plan.state == query.state]

        # Filter by labels (AND logic - all must match)
        if query.labels:
            plans = [plan for plan in plans if all(label in plan.labels for label in query.labels)]

        # Apply limit
        if query.limit:
            plans = plans[: query.limit]

        return plans

    def get_provider_name(self) -> str:
        """Get the provider name.

        Returns:
            "fake"
        """
        return "fake"
