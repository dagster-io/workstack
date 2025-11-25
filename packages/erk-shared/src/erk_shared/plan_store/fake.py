"""In-memory fake implementation for plan storage."""

from pathlib import Path

from erk_shared.plan_store.store import PlanStore
from erk_shared.plan_store.types import Plan, PlanQuery, PlanState


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
        self._closed_plans: list[str] = []

    @property
    def closed_plans(self) -> list[str]:
        """Read-only access to closed plans for test assertions.

        Returns list of plan identifiers that were closed.
        """
        return self._closed_plans

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

    def close_plan(self, repo_root: Path, identifier: str) -> None:
        """Close a plan in fake storage.

        Args:
            repo_root: Repository root directory (ignored in fake)
            identifier: Plan identifier

        Raises:
            RuntimeError: If plan identifier not found (simulates provider error)
        """
        if identifier not in self._plans:
            msg = f"Plan '{identifier}' not found"
            raise RuntimeError(msg)

        # Update plan state to closed
        current_plan = self._plans[identifier]
        self._plans[identifier] = Plan(
            plan_identifier=current_plan.plan_identifier,
            title=current_plan.title,
            body=current_plan.body,
            state=PlanState.CLOSED,
            url=current_plan.url,
            labels=current_plan.labels,
            assignees=current_plan.assignees,
            created_at=current_plan.created_at,
            updated_at=current_plan.updated_at,
            metadata=current_plan.metadata,
        )
        self._closed_plans.append(identifier)
