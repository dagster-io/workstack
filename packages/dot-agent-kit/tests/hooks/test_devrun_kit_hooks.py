"""Integration tests for devrun kit hook installation."""

from pathlib import Path

from dot_agent_kit.hooks.installer import install_hooks
from dot_agent_kit.hooks.models import HookDefinition
from dot_agent_kit.hooks.settings import load_settings


def test_devrun_kit_installs_both_hooks(tmp_project: Path) -> None:
    """Test that devrun kit installs both UserPromptSubmit and PreToolUse hooks."""
    # Define hooks matching devrun kit.yaml
    hooks = [
        HookDefinition(
            id="devrun-reminder-hook",
            lifecycle="UserPromptSubmit",
            matcher="*",
            invocation="dot-agent run devrun devrun-reminder-hook",
            description="Output devrun agent reminder on every prompt",
            timeout=30,
        ),
        HookDefinition(
            id="bash-validator-hook",
            lifecycle="PreToolUse",
            matcher="Bash",
            invocation="dot-agent run devrun bash-validator-hook",
            description="Block direct dev tool usage, enforce devrun agent",
            timeout=30,
        ),
    ]

    # Install hooks
    count = install_hooks(
        kit_id="devrun",
        hooks=hooks,
        project_root=tmp_project,
    )

    # Verify installation count
    assert count == 2

    # Load and verify settings structure
    settings_path = tmp_project / ".claude" / "settings.json"
    assert settings_path.exists()

    settings = load_settings(settings_path)
    assert settings.hooks is not None

    # Verify UserPromptSubmit hook
    assert "UserPromptSubmit" in settings.hooks
    userprompt_hooks = settings.hooks["UserPromptSubmit"]
    assert len(userprompt_hooks) == 1
    assert userprompt_hooks[0].matcher == "*"
    userprompt_cmds = [hook.command for hook in userprompt_hooks[0].hooks]
    assert any("devrun-reminder-hook" in cmd for cmd in userprompt_cmds)

    # Verify PreToolUse hook
    assert "PreToolUse" in settings.hooks
    pretooluse_hooks = settings.hooks["PreToolUse"]
    assert len(pretooluse_hooks) == 1
    assert pretooluse_hooks[0].matcher == "Bash"
    pretooluse_cmds = [hook.command for hook in pretooluse_hooks[0].hooks]
    assert any("bash-validator-hook" in cmd for cmd in pretooluse_cmds)

    # Verify hook command includes environment variables
    bash_hook = pretooluse_hooks[0].hooks[0]
    assert "DOT_AGENT_KIT_ID=devrun" in bash_hook.command
    assert "DOT_AGENT_HOOK_ID=bash-validator-hook" in bash_hook.command
    assert bash_hook.timeout == 30
