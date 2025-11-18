"""Tests for rendering framework.

These tests verify the renderer abstraction for text and JSON output formats.
"""

from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from erk.cli.rendering import JsonRenderer, TextRenderer, get_renderer

# Test get_renderer factory function


def test_get_renderer_json() -> None:
    """get_renderer should return JsonRenderer for json format."""
    renderer = get_renderer("json")
    assert isinstance(renderer, JsonRenderer)


def test_get_renderer_text() -> None:
    """get_renderer should return TextRenderer for text format."""
    renderer = get_renderer("text")
    assert isinstance(renderer, TextRenderer)


def test_get_renderer_default_text() -> None:
    """get_renderer should default to TextRenderer for unknown formats."""
    renderer = get_renderer("unknown")
    assert isinstance(renderer, TextRenderer)


# Test TextRenderer


@patch("erk.cli.rendering.user_output")
def test_text_renderer_render_simple(mock_user_output: MagicMock) -> None:
    """TextRenderer should output key-value pairs."""
    renderer = TextRenderer()
    data = {"name": "test", "count": 42}
    renderer.render_simple(data)

    # Verify output calls
    assert mock_user_output.call_count == 2
    calls = [call("name: test"), call("count: 42")]
    mock_user_output.assert_has_calls(calls, any_order=True)


@patch("erk.cli.rendering.user_output")
def test_text_renderer_render_simple_empty(mock_user_output: MagicMock) -> None:
    """TextRenderer should handle empty dict."""
    renderer = TextRenderer()
    data = {}
    renderer.render_simple(data)

    mock_user_output.assert_not_called()


def test_text_renderer_render_list_not_implemented() -> None:
    """TextRenderer.render_list should raise NotImplementedError."""
    renderer = TextRenderer()
    with pytest.raises(
        NotImplementedError, match="must be implemented during list command refactoring"
    ):
        renderer.render_list({"worktrees": []})


@patch("erk.status.renderers.simple.SimpleRenderer")
def test_text_renderer_render_status(mock_simple_renderer_class: MagicMock) -> None:
    """TextRenderer should delegate to status SimpleRenderer."""
    mock_renderer_instance = MagicMock()
    mock_simple_renderer_class.return_value = mock_renderer_instance

    renderer = TextRenderer()
    status_data = MagicMock()
    renderer.render_status(status_data)

    # Verify SimpleRenderer was instantiated and called
    mock_simple_renderer_class.assert_called_once_with()
    mock_renderer_instance.render.assert_called_once_with(status_data)


# Test JsonRenderer


@patch("erk.cli.rendering.emit_json")
def test_json_renderer_render_simple(mock_emit_json: MagicMock) -> None:
    """JsonRenderer should emit data as JSON."""
    renderer = JsonRenderer()
    data = {"name": "test", "count": 42}
    renderer.render_simple(data)

    mock_emit_json.assert_called_once_with(data)


@patch("erk.cli.rendering.emit_json")
def test_json_renderer_render_simple_with_path(mock_emit_json: MagicMock) -> None:
    """JsonRenderer should handle Path objects via emit_json serialization."""
    renderer = JsonRenderer()
    data = {"path": Path("/test")}
    renderer.render_simple(data)

    # emit_json handles serialization, just verify it was called
    mock_emit_json.assert_called_once_with(data)


@patch("erk.cli.rendering.emit_json")
def test_json_renderer_render_list(mock_emit_json: MagicMock) -> None:
    """JsonRenderer should emit list data as JSON."""
    renderer = JsonRenderer()
    data = {"worktrees": [{"name": "test1"}, {"name": "test2"}]}
    renderer.render_list(data)

    mock_emit_json.assert_called_once_with(data)


@patch("erk.cli.rendering.emit_json")
def test_json_renderer_render_status_with_statusdata(mock_emit_json: MagicMock) -> None:
    """JsonRenderer should convert StatusData to Pydantic model and emit as JSON."""
    from erk.status.models.status_data import GitStatus, StatusData, WorktreeDisplayInfo

    renderer = JsonRenderer()
    worktree_info = WorktreeDisplayInfo.root(Path("/repo"))
    git_status = GitStatus.clean_status("main")
    status_data = StatusData.with_git_status(worktree_info, git_status)

    renderer.render_status(status_data)

    # Verify emit_json was called with dict (converted from Pydantic model)
    mock_emit_json.assert_called_once()
    dict_data = mock_emit_json.call_args[0][0]
    # Verify it's a dict with expected structure
    assert isinstance(dict_data, dict)
    assert dict_data["worktree_info"]["name"] == "root"
    assert dict_data["git_status"]["is_clean"] is True


@patch("erk.cli.rendering.emit_json")
def test_json_renderer_render_status_with_complex_data(mock_emit_json: MagicMock) -> None:
    """JsonRenderer should handle StatusData with all fields populated."""
    from erk.status.models.status_data import (
        GitStatus,
        PlanStatus,
        PullRequestStatus,
        StackPosition,
        StatusData,
        WorktreeDisplayInfo,
    )

    renderer = JsonRenderer()
    worktree_info = WorktreeDisplayInfo.feature(Path("/repo/wt"), "feature")
    git_status = GitStatus.clean_status("feature")
    stack_position = StackPosition(
        stack=["main", "feature"],
        current_branch="feature",
        parent_branch="main",
        children_branches=[],
        is_trunk=False,
    )
    pr_status = PullRequestStatus(
        number=123,
        title="Test PR",
        state="open",
        is_draft=False,
        url="https://github.com/test/repo/pull/123",
        checks_passing=True,
        reviews=None,
        ready_to_merge=True,
    )
    plan_status = PlanStatus(
        exists=True,
        path=Path("/repo/wt/.plan"),
        summary="Test plan",
        line_count=10,
        first_lines=["# Plan"],
        progress_summary="1/5 done",
        format="folder",
    )
    status_data = StatusData(
        worktree_info=worktree_info,
        git_status=git_status,
        stack_position=stack_position,
        pr_status=pr_status,
        environment=None,
        dependencies=None,
        plan=plan_status,
        related_worktrees=[],
    )

    renderer.render_status(status_data)

    # Verify emit_json was called with dict containing complete structure
    mock_emit_json.assert_called_once()
    dict_data = mock_emit_json.call_args[0][0]
    assert isinstance(dict_data, dict)
    assert dict_data["worktree_info"]["name"] == "wt"
    assert dict_data["stack"]["position"] == "leaf"
    assert dict_data["pr_status"]["number"] == 123
    assert dict_data["plan"]["exists"] is True


# Integration tests


@patch("erk.cli.rendering.user_output")
def test_text_renderer_preserves_output_routing(mock_user_output: MagicMock) -> None:
    """TextRenderer should route output to user_output (stderr)."""
    renderer = TextRenderer()
    renderer.render_simple({"test": "value"})

    # Verify user_output was called (routes to stderr)
    mock_user_output.assert_called()


@patch("erk.cli.rendering.emit_json")
def test_json_renderer_routes_to_stdout(mock_emit_json: MagicMock) -> None:
    """JsonRenderer should route output through emit_json (stdout via machine_output)."""
    renderer = JsonRenderer()
    renderer.render_simple({"test": "value"})

    # Verify emit_json was called (routes to stdout via machine_output)
    mock_emit_json.assert_called_once()


def test_renderer_interface_completeness() -> None:
    """Both renderers should implement all required methods."""
    text_renderer = TextRenderer()
    json_renderer = JsonRenderer()

    # Verify both have required methods
    assert hasattr(text_renderer, "render_simple")
    assert hasattr(text_renderer, "render_list")
    assert hasattr(text_renderer, "render_status")

    assert hasattr(json_renderer, "render_simple")
    assert hasattr(json_renderer, "render_list")
    assert hasattr(json_renderer, "render_status")


@patch("erk.cli.rendering.emit_json")
def test_json_renderer_handles_empty_data(mock_emit_json: MagicMock) -> None:
    """JsonRenderer should handle empty data structures."""
    renderer = JsonRenderer()

    renderer.render_simple({})
    mock_emit_json.assert_called_with({})

    renderer.render_list({"worktrees": []})
    mock_emit_json.assert_called_with({"worktrees": []})
