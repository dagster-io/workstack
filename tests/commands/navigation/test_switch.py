import os
import re
import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner

from workstack.cli.cli import cli
from workstack.cli.commands.shell_integration import hidden_shell_cmd


def strip_ansi(text: str) -> str:
    """Remove ANSI escape codes from text."""
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def test_switch_command(tmp_path: Path) -> None:
    """Test the switch command outputs activation script."""
    # Set up isolated global config
    global_config_dir = tmp_path / ".workstack"
    global_config_dir.mkdir()
    workstacks_root = tmp_path / "workstacks"
    (global_config_dir / "config.toml").write_text(
        f'workstacks_root = "{workstacks_root}"\nuse_graphite = false\n'
    )

    # Set up a fake git repo
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True)

    # Create an initial commit
    (repo / "README.md").write_text("test")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo, check=True)

    # Create a worktree using isolated config
    env = os.environ.copy()
    env["HOME"] = str(tmp_path)
    result = subprocess.run(
        ["uv", "run", "workstack", "create", "myfeature", "--no-post"],
        cwd=repo,
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0, f"Create failed: {result.stderr}"

    # Run switch command with --script flag
    result = subprocess.run(
        ["uv", "run", "workstack", "switch", "myfeature", "--script"],
        cwd=repo,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode == 0
    # Output should be a temp file path
    script_path = Path(result.stdout.strip())
    assert script_path.exists()
    assert script_path.name.startswith("workstack-switch-")
    assert script_path.name.endswith(".sh")

    # Verify script content
    script_content = script_path.read_text()
    assert "cd" in script_content
    assert str(workstacks_root / "repo" / "myfeature") in script_content
    # Should source activate if venv exists
    assert "activate" in script_content

    # Cleanup
    script_path.unlink(missing_ok=True)


def test_switch_nonexistent_worktree(tmp_path: Path) -> None:
    """Test switch command with non-existent worktree."""
    # Set up a fake git repo
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True)

    # Create an initial commit
    (repo / "README.md").write_text("test")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo, check=True)

    # Try to switch to non-existent worktree using CliRunner
    runner = CliRunner()

    original_cwd = os.getcwd()
    try:
        os.chdir(repo)
        result = runner.invoke(cli, ["switch", "doesnotexist"])

        assert result.exit_code != 0
        assert "not found" in result.output.lower()
    finally:
        os.chdir(original_cwd)


def test_switch_shell_completion() -> None:
    """Test that switch command has shell completion configured."""
    # This is a bit tricky to test without a real shell, but we can verify
    # the command is set up with the right completion function by checking help
    runner = CliRunner()
    result = runner.invoke(cli, ["switch", "--help"])

    assert result.exit_code == 0
    assert "NAME" in result.output


def test_switch_to_root(tmp_path: Path) -> None:
    """Test switching to root repo using 'root'."""
    # Set up isolated global config
    global_config_dir = tmp_path / ".workstack"
    global_config_dir.mkdir()
    workstacks_root = tmp_path / "workstacks"
    (global_config_dir / "config.toml").write_text(
        f'workstacks_root = "{workstacks_root}"\nuse_graphite = false\n'
    )

    # Set up a fake git repo
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True)

    # Create an initial commit
    (repo / "README.md").write_text("test")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo, check=True)

    # Run switch command with "root" and --script flag, using isolated config
    env = os.environ.copy()
    env["HOME"] = str(tmp_path)
    result = subprocess.run(
        ["uv", "run", "workstack", "switch", "root", "--script"],
        cwd=repo,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode == 0
    # Output should be a temp file path
    script_path = Path(result.stdout.strip())
    assert script_path.exists()
    assert script_path.name.startswith("workstack-switch-")
    assert script_path.name.endswith(".sh")

    # Verify script content
    script_content = script_path.read_text()
    assert "cd" in script_content
    assert str(repo) in script_content
    assert "root" in script_content.lower()

    # Cleanup
    script_path.unlink(missing_ok=True)


def test_hidden_shell_cmd_switch_passthrough_on_help() -> None:
    """Shell integration wrapper defers to regular switch help."""
    runner = CliRunner()
    result = runner.invoke(hidden_shell_cmd, ["switch", "--help"])

    assert result.exit_code == 0
    assert result.output.strip() == "__WORKSTACK_PASSTHROUGH__"


def test_list_includes_root(tmp_path: Path) -> None:
    """Test that list command shows root repo with branch name."""
    # Set up isolated global config
    global_config_dir = tmp_path / ".workstack"
    global_config_dir.mkdir()
    workstacks_root = tmp_path / "workstacks"
    (global_config_dir / "config.toml").write_text(
        f'workstacks_root = "{workstacks_root}"\nuse_graphite = false\n'
    )

    # Set up a fake git repo
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True)

    # Create an initial commit
    (repo / "README.md").write_text("test")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo, check=True)

    # Create a worktree using isolated config
    env = os.environ.copy()
    env["HOME"] = str(tmp_path)
    subprocess.run(
        ["uv", "run", "workstack", "create", "myfeature", "--no-post"],
        cwd=repo,
        capture_output=True,
        text=True,
        env=env,
    )

    # List worktrees
    result = subprocess.run(
        ["uv", "run", "workstack", "list"],
        cwd=repo,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode == 0
    # Should show root as first entry
    clean_output = strip_ansi(result.stdout)
    lines = clean_output.strip().split("\n")
    assert len(lines) >= 2
    # Check that first line shows the root worktree
    assert lines[0].startswith("root")
    # Should also show the created worktree
    assert any("myfeature" in line for line in lines)


def test_complete_worktree_names_without_context(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test completion function works even when Click context obj is None.

    This simulates the shell completion scenario where the CLI group callback
    hasn't run yet, so ctx.obj is None.
    """
    import click

    from tests.fakes.shell_ops import FakeShellOps
    from workstack.cli.cli import cli
    from workstack.cli.commands.switch import complete_worktree_names
    from workstack.core.context import WorkstackContext
    from workstack.core.github_ops import RealGitHubOps
    from workstack.core.gitops import RealGitOps
    from workstack.core.global_config import load_global_config
    from workstack.core.graphite_ops import RealGraphiteOps

    # Set up isolated global config
    global_config_dir = tmp_path / ".workstack"
    global_config_dir.mkdir()
    workstacks_root = tmp_path / "workstacks"
    (global_config_dir / "config.toml").write_text(
        f'workstacks_root = "{workstacks_root}"\nuse_graphite = false\n',
        encoding="utf-8",
    )

    # Set up a fake git repo
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True)

    # Create initial commit
    (repo / "README.md").write_text("test")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial"], cwd=repo, check=True, capture_output=True)

    # Create worktrees
    env = os.environ.copy()
    env["HOME"] = str(tmp_path)
    for name in ["feature-a", "feature-b", "bugfix-123"]:
        subprocess.run(
            ["uv", "run", "workstack", "create", name, "--no-post"],
            cwd=repo,
            capture_output=True,
            env=env,
        )

    # Mock create_context to use test environment
    # NOTE: Use FakeShellOps to avoid any risk of mutating user shell config files
    def mock_create_context() -> WorkstackContext:
        # Load global config from test environment
        global_config = load_global_config()
        return WorkstackContext.for_test(
            git_ops=RealGitOps(),
            global_config=global_config,
            github_ops=RealGitHubOps(),
            graphite_ops=RealGraphiteOps(),
            shell_ops=FakeShellOps(),
            cwd=repo,
            dry_run=False,
        )

    # Patch Path.home() to return tmp_path so config loading uses test config
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

    # Create a mock Click context with NO obj (simulates shell completion scenario)
    ctx = click.Context(cli)
    ctx.obj = None  # This is the critical test condition

    # Change to repo directory for completion
    original_cwd = os.getcwd()
    try:
        os.chdir(repo)

        # Call completion function
        completions = complete_worktree_names(ctx, None, "")

        # Should return worktree names even without ctx.obj
        assert "root" in completions
        assert "feature-a" in completions
        assert "feature-b" in completions
        assert "bugfix-123" in completions

        # Test filtering by prefix
        completions = complete_worktree_names(ctx, None, "feat")
        assert "feature-a" in completions
        assert "feature-b" in completions
        assert "bugfix-123" not in completions

    finally:
        os.chdir(original_cwd)


def test_switch_rejects_main_as_worktree_name(tmp_path: Path) -> None:
    """Test that 'main' is rejected with helpful error."""
    # Set up isolated global config
    global_config_dir = tmp_path / ".workstack"
    global_config_dir.mkdir()
    workstacks_root = tmp_path / "workstacks"
    (global_config_dir / "config.toml").write_text(
        f'workstacks_root = "{workstacks_root}"\nuse_graphite = false\n'
    )

    # Set up a fake git repo
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True)

    # Create an initial commit
    (repo / "README.md").write_text("test")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo, check=True)

    # Try to switch to "main" using CliRunner
    env_vars = os.environ.copy()
    env_vars["HOME"] = str(tmp_path)
    runner = CliRunner(env=env_vars)

    original_cwd = os.getcwd()
    try:
        os.chdir(repo)
        result = runner.invoke(cli, ["switch", "main"])

        # Should fail with error suggesting to use root
        assert result.exit_code != 0
        assert "main" in result.output.lower()
        assert "workstack switch root" in result.output
    finally:
        os.chdir(original_cwd)


def test_switch_rejects_master_as_worktree_name(tmp_path: Path) -> None:
    """Test that 'master' is rejected with helpful error."""
    # Set up isolated global config
    global_config_dir = tmp_path / ".workstack"
    global_config_dir.mkdir()
    workstacks_root = tmp_path / "workstacks"
    (global_config_dir / "config.toml").write_text(
        f'workstacks_root = "{workstacks_root}"\nuse_graphite = false\n'
    )

    # Set up a fake git repo
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "master"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True)

    # Create an initial commit
    (repo / "README.md").write_text("test")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo, check=True)

    # Try to switch to "master" using CliRunner
    env_vars = os.environ.copy()
    env_vars["HOME"] = str(tmp_path)
    runner = CliRunner(env=env_vars)

    original_cwd = os.getcwd()
    try:
        os.chdir(repo)
        result = runner.invoke(cli, ["switch", "master"])

        # Should fail with error suggesting to use root
        assert result.exit_code != 0
        assert "master" in result.output.lower()
        assert "workstack switch root" in result.output
    finally:
        os.chdir(original_cwd)
