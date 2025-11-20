"""Tests for GitHub trigger_workflow() method."""

from pathlib import Path

from tests.fakes.github import FakeGitHub


def test_trigger_workflow_tracks_call() -> None:
    """Verify FakeGitHub records workflow triggers."""
    github = FakeGitHub()
    repo_root = Path("/repo")

    github.trigger_workflow(
        repo_root,
        "implement-plan.yml",
        {"branch-name": "feature"},
    )

    assert len(github.triggered_workflows) == 1
    workflow, inputs = github.triggered_workflows[0]
    assert workflow == "implement-plan.yml"
    assert inputs == {"branch-name": "feature"}


def test_trigger_workflow_tracks_multiple_calls() -> None:
    """Verify multiple workflow triggers are tracked."""
    github = FakeGitHub()
    repo_root = Path("/repo")

    github.trigger_workflow(repo_root, "workflow1.yml", {"key": "value1"})
    github.trigger_workflow(repo_root, "workflow2.yml", {"key": "value2"})

    assert len(github.triggered_workflows) == 2
    assert github.triggered_workflows[0][0] == "workflow1.yml"
    assert github.triggered_workflows[1][0] == "workflow2.yml"
