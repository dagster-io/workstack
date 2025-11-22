"""Provider-agnostic abstraction for plan issue storage.

This module provides interfaces and implementations for storing and retrieving
plan issues across different providers (GitHub, GitLab, Linear, Jira, etc.).
"""

from erk.core.plan_issue_store.fake import FakePlanIssueStore
from erk.core.plan_issue_store.github import GitHubPlanIssueStore
from erk.core.plan_issue_store.store import PlanIssueStore
from erk.core.plan_issue_store.types import PlanIssue, PlanIssueQuery, PlanIssueState

__all__ = [
    "PlanIssue",
    "PlanIssueQuery",
    "PlanIssueState",
    "PlanIssueStore",
    "GitHubPlanIssueStore",
    "FakePlanIssueStore",
]
