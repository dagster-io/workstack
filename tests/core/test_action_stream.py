"""Tests for action stream infrastructure."""

from pathlib import Path

from workstack.core.action_stream import Action, DryRunStream, ProductionStream
from workstack.core.context import create_context


def test_production_stream_executes_actions() -> None:
    """Test that ProductionStream executes actions and returns results."""
    ctx = create_context(dry_run=False)
    stream = ProductionStream(ctx)

    # Track execution with a mutable list
    executed: list[str] = []

    def executor() -> str:
        executed.append("action_executed")
        return "result_value"

    action = Action(description="Test action", executor=executor)

    result = stream.execute(action)

    # Verify executor was called and result returned
    assert executed == ["action_executed"]
    assert result == "result_value"


def test_production_stream_stores_results_when_result_key_provided() -> None:
    """Test that ProductionStream stores results in results dict when result_key is set."""
    ctx = create_context(dry_run=False)
    stream = ProductionStream(ctx)

    actions = [
        Action.with_result("Get value 1", lambda: "first_value", result_key="key1"),
        Action.with_result("Get value 2", lambda: "second_value", result_key="key2"),
    ]

    stream.run(actions)

    # Verify results stored correctly
    assert stream.results["key1"] == "first_value"
    assert stream.results["key2"] == "second_value"


def test_dry_run_stream_does_not_execute_actions(capsys: object) -> None:
    """Test that DryRunStream prints messages without executing actions."""
    ctx = create_context(dry_run=False)
    stream = DryRunStream(ctx)

    # Track execution with a mutable list
    executed: list[str] = []

    def executor() -> str:
        executed.append("should_not_execute")
        return "should_not_return"

    action = Action(description="Test dry-run action", executor=executor)

    result = stream.execute(action)

    # Verify executor was NOT called
    assert executed == []
    assert result is None

    # Verify message was printed
    captured = capsys.readouterr()  # type: ignore
    assert "(dry run)" in captured.out
    assert "Would: Test dry-run action" in captured.out


def test_dry_run_stream_does_not_store_results() -> None:
    """Test that DryRunStream does not store results even when result_key is set."""
    ctx = create_context(dry_run=False)
    stream = DryRunStream(ctx)

    actions = [
        Action.with_result("Get value", lambda: "value", result_key="key1"),
    ]

    stream.run(actions)

    # Verify results NOT stored (DryRunStream.execute returns None)
    assert stream.results["key1"] is None


def test_reactive_dependencies_in_production_stream() -> None:
    """Test that actions can access results from earlier actions."""
    ctx = create_context(dry_run=False)
    stream = ProductionStream(ctx)

    # First action stores a result
    # Second action uses that result
    actions = [
        Action.with_result("Compute base value", lambda: 10, result_key="base"),
        Action.with_result(
            "Double base value",
            # Access stream.results from within executor
            lambda: stream.results["base"] * 2 if "base" in stream.results else 0,  # type: ignore
            result_key="doubled",
        ),
    ]

    stream.run(actions)

    # Verify reactive dependency worked
    assert stream.results["base"] == 10
    assert stream.results["doubled"] == 20


def test_git_checkout_builder_creates_action() -> None:
    """Test that Action.git_checkout creates valid action."""
    ctx = create_context(dry_run=False)
    repo_root = Path("/test/repo")
    branch = "feature-branch"

    action = Action.git_checkout(ctx, repo_root, branch)

    # Verify action properties
    assert action.description == "Checkout branch: feature-branch"
    assert action.executor is not None
    assert action.result_key is None


def test_git_add_worktree_builder_creates_action() -> None:
    """Test that Action.git_add_worktree creates valid action."""
    ctx = create_context(dry_run=False)
    repo_root = Path("/test/repo")
    worktree_path = Path("/test/worktree")
    branch = "feature-branch"

    action = Action.git_add_worktree(ctx, repo_root, worktree_path, branch)

    # Verify action properties
    assert "Add worktree at" in action.description
    assert "feature-branch" in action.description
    assert action.executor is not None
    assert action.result_key is None


def test_git_remove_worktree_builder_creates_action() -> None:
    """Test that Action.git_remove_worktree creates valid action."""
    ctx = create_context(dry_run=False)
    repo_root = Path("/test/repo")
    worktree_path = Path("/test/worktree")

    action = Action.git_remove_worktree(ctx, repo_root, worktree_path)

    # Verify action properties
    assert "Remove worktree at" in action.description
    assert action.executor is not None
    assert action.result_key is None


def test_subprocess_run_builder_creates_action() -> None:
    """Test that Action.subprocess_run creates valid action."""
    description = "Run merge command"
    cmd = ["gh", "pr", "merge", "123"]
    cwd = Path("/test/repo")

    action = Action.subprocess_run(description, cmd, cwd)

    # Verify action properties
    assert action.description == "Run merge command"
    assert action.executor is not None
    assert action.result_key is None


def test_graphite_sync_builder_creates_action() -> None:
    """Test that Action.graphite_sync creates valid action."""
    ctx = create_context(dry_run=False)
    repo_root = Path("/test/repo")

    action = Action.graphite_sync(ctx, repo_root, force=True)

    # Verify action properties
    assert "Run graphite sync" in action.description
    assert "force=True" in action.description
    assert action.executor is not None
    assert action.result_key is None


def test_with_result_builder_creates_action_with_result_key() -> None:
    """Test that Action.with_result creates action with result_key set."""

    def sample_executor() -> str:
        return "test_result"

    action = Action.with_result("Get test result", sample_executor, result_key="test_key")

    # Verify action properties
    assert action.description == "Get test result"
    assert action.executor is not None
    assert action.result_key == "test_key"


def test_action_stream_run_executes_multiple_actions_sequentially() -> None:
    """Test that ActionStream.run executes actions in order."""
    ctx = create_context(dry_run=False)
    stream = ProductionStream(ctx)

    # Track execution order
    execution_order: list[int] = []

    actions = [
        Action("First action", lambda: execution_order.append(1)),
        Action("Second action", lambda: execution_order.append(2)),
        Action("Third action", lambda: execution_order.append(3)),
    ]

    stream.run(actions)

    # Verify sequential execution
    assert execution_order == [1, 2, 3]


def test_lambda_capture_with_builders_is_safe() -> None:
    """Test that builder methods handle lambda capture correctly (avoid closure bugs)."""
    ctx = create_context(dry_run=False)

    # Simulate loop where naive lambda would capture last value
    branches = ["branch-1", "branch-2", "branch-3"]
    actions: list[Action] = []

    for branch in branches:
        # Builder methods should handle parameter binding safely
        actions.append(Action.git_checkout(ctx, Path("/repo"), branch))

    # Execute all actions and verify descriptions are correct
    # (If lambda capture was wrong, all would say "branch-3")
    descriptions = [action.description for action in actions]

    assert descriptions == [
        "Checkout branch: branch-1",
        "Checkout branch: branch-2",
        "Checkout branch: branch-3",
    ]


def test_production_stream_accepts_verbose_parameter() -> None:
    """Test that ProductionStream can be initialized with verbose parameter."""
    ctx = create_context(dry_run=False)

    # Test with verbose=True
    verbose_stream = ProductionStream(ctx, verbose=True)
    assert verbose_stream.verbose is True

    # Test with verbose=False (default)
    quiet_stream = ProductionStream(ctx, verbose=False)
    assert quiet_stream.verbose is False

    # Test default value
    default_stream = ProductionStream(ctx)
    assert default_stream.verbose is False


def test_dry_run_stream_accepts_verbose_parameter() -> None:
    """Test that DryRunStream can be initialized with verbose parameter."""
    ctx = create_context(dry_run=False)

    # Test with verbose=True
    verbose_stream = DryRunStream(ctx, verbose=True)
    assert verbose_stream.verbose is True

    # Test with verbose=False (default)
    quiet_stream = DryRunStream(ctx, verbose=False)
    assert quiet_stream.verbose is False

    # Test default value
    default_stream = DryRunStream(ctx)
    assert default_stream.verbose is False


def test_graphite_sync_accepts_quiet_parameter() -> None:
    """Test that Action.graphite_sync accepts quiet parameter."""
    ctx = create_context(dry_run=False)
    repo_root = Path("/test/repo")

    # Test with quiet=True (default)
    action_quiet = Action.graphite_sync(ctx, repo_root, force=True, quiet=True)
    assert "quiet=True" in action_quiet.description

    # Test with quiet=False
    action_verbose = Action.graphite_sync(ctx, repo_root, force=True, quiet=False)
    assert "quiet=False" in action_verbose.description

    # Test default value
    action_default = Action.graphite_sync(ctx, repo_root, force=True)
    assert "quiet=True" in action_default.description
