"""Tests for deprecated command migration errors."""

from click.testing import CliRunner

from erk.cli.cli import cli
from tests.fakes.gitops import FakeGitOps
from tests.test_utils.env_helpers import erk_inmem_env


def test_split_deprecated_shows_migration_message() -> None:
    """Test deprecated split command shows migration error."""
    runner = CliRunner()

    with erk_inmem_env(runner) as env:
        git_ops = FakeGitOps(
            git_common_dirs={env.cwd: env.git_dir},
        )

        ctx = env.build_context(git_ops=git_ops)

        result = runner.invoke(cli, ["split"], obj=ctx)

        assert result.exit_code == 1
        assert "has been replaced" in result.output
        assert "erk forest split" in result.output
        assert "--help" in result.output


def test_consolidate_deprecated_shows_migration_message() -> None:
    """Test deprecated consolidate command shows migration error."""
    runner = CliRunner()

    with erk_inmem_env(runner) as env:
        git_ops = FakeGitOps(
            git_common_dirs={env.cwd: env.git_dir},
        )

        ctx = env.build_context(git_ops=git_ops)

        result = runner.invoke(cli, ["consolidate"], obj=ctx)

        assert result.exit_code == 1
        assert "has been replaced" in result.output
        assert "erk forest merge" in result.output
        assert "--name flag is no longer needed" in result.output
        assert "--help" in result.output


def test_split_deprecated_exit_code() -> None:
    """Test deprecated split command exits with code 1."""
    runner = CliRunner()

    with erk_inmem_env(runner) as env:
        git_ops = FakeGitOps(
            git_common_dirs={env.cwd: env.git_dir},
        )

        ctx = env.build_context(git_ops=git_ops)

        result = runner.invoke(cli, ["split"], obj=ctx)

        assert result.exit_code == 1


def test_consolidate_deprecated_exit_code() -> None:
    """Test deprecated consolidate command exits with code 1."""
    runner = CliRunner()

    with erk_inmem_env(runner) as env:
        git_ops = FakeGitOps(
            git_common_dirs={env.cwd: env.git_dir},
        )

        ctx = env.build_context(git_ops=git_ops)

        result = runner.invoke(cli, ["consolidate"], obj=ctx)

        assert result.exit_code == 1
