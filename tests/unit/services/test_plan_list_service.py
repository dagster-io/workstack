"""Tests for PlanListService."""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from erk_shared.github.issues import FakeGitHubIssues, IssueInfo
from erk_shared.github.types import PullRequestInfo, WorkflowRun

from erk.core.github.fake import FakeGitHub
from erk.core.services.plan_list_service import PlanListData, PlanListService


class TestPlanListService:
    """Tests for PlanListService with injected fakes."""

    def test_fetches_issues_from_github_issues_integration(self) -> None:
        """Service delegates issue fetching to GitHubIssues integration."""
        now = datetime.now(UTC)
        issue = IssueInfo(
            number=42,
            title="Test Plan",
            body="Plan body",
            state="OPEN",
            url="https://github.com/owner/repo/issues/42",
            labels=["erk-plan"],
            assignees=[],
            created_at=now,
            updated_at=now,
        )
        fake_issues = FakeGitHubIssues(issues={42: issue})
        fake_github = FakeGitHub()

        service = PlanListService(fake_github, fake_issues)
        result = service.get_plan_list_data(
            repo_root=Path("/test/repo"),
            labels=["erk-plan"],
        )

        assert len(result.issues) == 1
        assert result.issues[0].number == 42
        assert result.issues[0].title == "Test Plan"

    def test_fetches_pr_linkages_from_github_integration(self) -> None:
        """Service delegates PR linkage fetching to GitHub integration."""
        now = datetime.now(UTC)
        issue = IssueInfo(
            number=42,
            title="Test Plan",
            body="",
            state="OPEN",
            url="",
            labels=["erk-plan"],
            assignees=[],
            created_at=now,
            updated_at=now,
        )
        pr = PullRequestInfo(
            number=123,
            state="OPEN",
            url="https://github.com/owner/repo/pull/123",
            is_draft=False,
            title="PR Title",
            checks_passing=True,
            owner="owner",
            repo="repo",
        )
        fake_issues = FakeGitHubIssues(issues={42: issue})
        fake_github = FakeGitHub(pr_issue_linkages={42: [pr]})

        service = PlanListService(fake_github, fake_issues)
        result = service.get_plan_list_data(
            repo_root=Path("/test/repo"),
            labels=["erk-plan"],
        )

        assert 42 in result.pr_linkages
        assert result.pr_linkages[42][0].number == 123

    def test_empty_issues_returns_empty_data(self) -> None:
        """Service returns empty data when no issues match."""
        fake_issues = FakeGitHubIssues()
        fake_github = FakeGitHub()

        service = PlanListService(fake_github, fake_issues)
        result = service.get_plan_list_data(
            repo_root=Path("/test/repo"),
            labels=["erk-plan"],
        )

        assert result.issues == []
        assert result.pr_linkages == {}
        assert result.workflow_runs == {}

    def test_state_filter_passed_to_integration(self) -> None:
        """Service passes state filter to GitHubIssues integration."""
        now = datetime.now(UTC)
        open_issue = IssueInfo(
            number=1,
            title="Open Plan",
            body="",
            state="OPEN",
            url="",
            labels=["erk-plan"],
            assignees=[],
            created_at=now,
            updated_at=now,
        )
        closed_issue = IssueInfo(
            number=2,
            title="Closed Plan",
            body="",
            state="CLOSED",
            url="",
            labels=["erk-plan"],
            assignees=[],
            created_at=now,
            updated_at=now,
        )
        fake_issues = FakeGitHubIssues(issues={1: open_issue, 2: closed_issue})
        fake_github = FakeGitHub()

        service = PlanListService(fake_github, fake_issues)
        result = service.get_plan_list_data(
            repo_root=Path("/test/repo"),
            labels=["erk-plan"],
            state="open",
        )

        assert len(result.issues) == 1
        assert result.issues[0].title == "Open Plan"


class TestPlanListData:
    """Tests for PlanListData dataclass."""

    def test_dataclass_is_frozen(self) -> None:
        """PlanListData instances are immutable."""
        data = PlanListData(
            issues=[],
            pr_linkages={},
            workflow_runs={},
        )

        with pytest.raises(AttributeError):
            data.issues = []  # type: ignore[misc]

    def test_dataclass_contains_all_fields(self) -> None:
        """PlanListData has all expected fields."""
        now = datetime.now(UTC)
        issues = [
            IssueInfo(
                number=1,
                title="Plan",
                body="",
                state="OPEN",
                url="",
                labels=[],
                assignees=[],
                created_at=now,
                updated_at=now,
            )
        ]
        pr = PullRequestInfo(
            number=10,
            state="OPEN",
            url="",
            is_draft=False,
            title="PR",
            checks_passing=True,
            owner="owner",
            repo="repo",
        )
        linkages = {1: [pr]}
        run = WorkflowRun(
            run_id="100",
            status="completed",
            conclusion="success",
            branch="main",
            head_sha="abc",
        )
        runs: dict[int, WorkflowRun | None] = {1: run}

        data = PlanListData(
            issues=issues,
            pr_linkages=linkages,
            workflow_runs=runs,
        )

        assert data.issues == issues
        assert data.pr_linkages == linkages
        assert data.workflow_runs == runs
