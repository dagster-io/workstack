"""Tests for the __prepare_cwd_recovery hidden command."""

import os
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.prepare_cwd_recovery import prepare_cwd_recovery_cmd
from erk.core.context import WorkstackContext
from erk.core.global_config import GlobalConfig
from tests.fakes.context import create_test_context
from tests.fakes.gitops import FakeGitOps
from tests.fakes.script_writer import FakeScriptWriterOps


def build_ctx(
    repo_root: Path | None, workstacks_root: Path, cwd: Path | None = None
) -> WorkstackContext:
    """Create a WorkstackContext with test fakes."""
    git_common_dirs: dict[Path, Path] = {}
    existing_paths: set[Path] = {workstacks_root}

    if repo_root is not None:
        git_common_dirs[repo_root] = repo_root / ".git"
        existing_paths.update({repo_root, repo_root / ".git"})

    # Add cwd to existing_paths if specified and different from repo_root
    if cwd is not None and cwd != repo_root:
        existing_paths.add(cwd)

    git_ops = FakeGitOps(git_common_dirs=git_common_dirs, existing_paths=existing_paths)
    script_writer = FakeScriptWriterOps()
    global_config_ops = GlobalConfig(
        workstacks_root=workstacks_root,
        use_graphite=False,
        shell_setup_complete=False,
        show_pr_info=True,
    )
    return create_test_context(
        git_ops=git_ops,
        script_writer=script_writer,
        global_config=global_config_ops,
        cwd=cwd or repo_root or workstacks_root,
        dry_run=False,
    )


def test_prepare_cwd_recovery_outputs_script(tmp_path: Path) -> None:
    """Command should emit a script path when inside a repo."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()

    workstacks_root = tmp_path / "workstacks"
    workstacks_root.mkdir()

    ctx = build_ctx(repo, workstacks_root, cwd=repo)

    runner = CliRunner()

    original_cwd = os.getcwd()
    try:
        os.chdir(repo)
        result = runner.invoke(prepare_cwd_recovery_cmd, obj=ctx)
    finally:
        os.chdir(original_cwd)

    assert result.exit_code == 0
    script_path = Path(result.output.strip())
    # Verify script was written to in-memory fake
    assert ctx.script_writer.get_script_content(script_path) is not None


def test_prepare_cwd_recovery_no_repo(tmp_path: Path) -> None:
    """Command should emit nothing outside a repository."""
    workstacks_root = tmp_path / "workstacks"
    workstacks_root.mkdir()

    ctx = build_ctx(None, workstacks_root)

    runner = CliRunner()

    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        result = runner.invoke(prepare_cwd_recovery_cmd, obj=ctx)
    finally:
        os.chdir(original_cwd)

    assert result.exit_code == 0
    assert result.output == ""


def test_prepare_cwd_recovery_missing_cwd(tmp_path: Path) -> None:
    """Command should handle missing cwd gracefully."""
    ctx = build_ctx(None, tmp_path)

    broken_dir = tmp_path / "vanish"
    broken_dir.mkdir()

    runner = CliRunner()

    original_cwd = os.getcwd()
    try:
        os.chdir(broken_dir)
        broken_dir.rmdir()
        result = runner.invoke(prepare_cwd_recovery_cmd, obj=ctx)
    finally:
        os.chdir(original_cwd)

    assert result.exit_code == 0
    assert result.output == ""
