"""Unit tests for bash validator PreToolUse hook."""

import json
import subprocess


def test_blocks_pytest() -> None:
    """Test that hook blocks direct pytest usage."""
    input_data = {"tool_name": "Bash", "tool_input": {"command": "pytest tests/"}}

    result = subprocess.run(
        ["uv", "run", "dot-agent", "run", "devrun", "bash-validator-hook"],
        input=json.dumps(input_data),
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert "Direct Bash usage blocked" in result.stderr
    assert "devrun agent" in result.stderr
    assert "pytest" in result.stderr


def test_blocks_uv_run_pytest() -> None:
    """Test that hook blocks uv run pytest usage."""
    input_data = {"tool_name": "Bash", "tool_input": {"command": "uv run pytest -v"}}

    result = subprocess.run(
        ["uv", "run", "dot-agent", "run", "devrun", "bash-validator-hook"],
        input=json.dumps(input_data),
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert "Direct Bash usage blocked" in result.stderr
    assert "pytest" in result.stderr


def test_blocks_pyright() -> None:
    """Test that hook blocks direct pyright usage."""
    input_data = {"tool_name": "Bash", "tool_input": {"command": "pyright src/"}}

    result = subprocess.run(
        ["uv", "run", "dot-agent", "run", "devrun", "bash-validator-hook"],
        input=json.dumps(input_data),
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert "Direct Bash usage blocked" in result.stderr
    assert "pyright" in result.stderr


def test_blocks_ruff() -> None:
    """Test that hook blocks direct ruff usage."""
    input_data = {"tool_name": "Bash", "tool_input": {"command": "ruff check ."}}

    result = subprocess.run(
        ["uv", "run", "dot-agent", "run", "devrun", "bash-validator-hook"],
        input=json.dumps(input_data),
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert "Direct Bash usage blocked" in result.stderr
    assert "ruff" in result.stderr


def test_blocks_prettier() -> None:
    """Test that hook blocks direct prettier usage."""
    input_data = {
        "tool_name": "Bash",
        "tool_input": {"command": "prettier --check"},
    }

    result = subprocess.run(
        ["uv", "run", "dot-agent", "run", "devrun", "bash-validator-hook"],
        input=json.dumps(input_data),
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert "Direct Bash usage blocked" in result.stderr
    assert "prettier" in result.stderr


def test_blocks_make() -> None:
    """Test that hook blocks direct make usage."""
    input_data = {"tool_name": "Bash", "tool_input": {"command": "make all-ci"}}

    result = subprocess.run(
        ["uv", "run", "dot-agent", "run", "devrun", "bash-validator-hook"],
        input=json.dumps(input_data),
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert "Direct Bash usage blocked" in result.stderr
    assert "make" in result.stderr


def test_blocks_gt() -> None:
    """Test that hook blocks direct gt usage."""
    input_data = {"tool_name": "Bash", "tool_input": {"command": "gt stack"}}

    result = subprocess.run(
        ["uv", "run", "dot-agent", "run", "devrun", "bash-validator-hook"],
        input=json.dumps(input_data),
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert "Direct Bash usage blocked" in result.stderr
    assert "gt" in result.stderr


def test_allows_git() -> None:
    """Test that hook allows git commands."""
    input_data = {"tool_name": "Bash", "tool_input": {"command": "git status"}}

    result = subprocess.run(
        ["uv", "run", "dot-agent", "run", "devrun", "bash-validator-hook"],
        input=json.dumps(input_data),
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stderr == ""


def test_allows_ls() -> None:
    """Test that hook allows ls commands."""
    input_data = {"tool_name": "Bash", "tool_input": {"command": "ls -la"}}

    result = subprocess.run(
        ["uv", "run", "dot-agent", "run", "devrun", "bash-validator-hook"],
        input=json.dumps(input_data),
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stderr == ""


def test_allows_echo() -> None:
    """Test that hook allows echo commands."""
    input_data = {"tool_name": "Bash", "tool_input": {"command": "echo hello"}}

    result = subprocess.run(
        ["uv", "run", "dot-agent", "run", "devrun", "bash-validator-hook"],
        input=json.dumps(input_data),
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stderr == ""


def test_allows_non_bash_tool() -> None:
    """Test that hook allows non-Bash tools."""
    input_data = {"tool_name": "Read", "tool_input": {"file_path": "test.txt"}}

    result = subprocess.run(
        ["uv", "run", "dot-agent", "run", "devrun", "bash-validator-hook"],
        input=json.dumps(input_data),
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stderr == ""
