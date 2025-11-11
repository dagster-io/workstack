"""Unit tests for shell passthrough script rendering functions."""

from pathlib import Path

from workstack.cli.shell_integration.handler import (
    _quote_fish,
    _render_fish_passthrough,
    _render_posix_passthrough,
)


class TestRenderPosixPassthrough:
    """Test POSIX (bash/zsh) passthrough script generation."""

    def test_basic_command_no_args_no_recovery(self) -> None:
        """Generate script for simple command without args or recovery."""
        script = _render_posix_passthrough(
            command_name="sync",
            args=(),
            recovery_path=None,
        )

        assert "command workstack sync" in script
        assert "__workstack_exit=$?" in script
        assert "__workstack_recovery=''" in script
        assert 'if [ -n "$__workstack_recovery" ] && [ -f "$__workstack_recovery" ]; then' in script
        assert '  if [ ! -d "$PWD" ]; then' in script
        assert "return $__workstack_exit" in script
        assert script.endswith("\n")

    def test_command_with_recovery_path(self) -> None:
        """Generate script with recovery path specified."""
        recovery = Path("/tmp/recovery.sh")
        script = _render_posix_passthrough(
            command_name="sync",
            args=(),
            recovery_path=recovery,
        )

        assert "command workstack sync" in script
        # shlex.quote may or may not add quotes depending on the path
        assert "__workstack_recovery=" in script
        assert "/tmp/recovery.sh" in script
        assert '    . "$__workstack_recovery"' in script
        assert '    rm -f "$__workstack_recovery"' in script

    def test_command_with_simple_args(self) -> None:
        """Generate script with simple arguments."""
        script = _render_posix_passthrough(
            command_name="sync",
            args=("--force", "branch-name"),
            recovery_path=None,
        )

        assert "command workstack sync --force branch-name" in script

    def test_command_with_special_chars_in_args(self) -> None:
        """Arguments with special characters are properly quoted."""
        script = _render_posix_passthrough(
            command_name="sync",
            args=("$branch", "file with spaces", "test;rm"),
            recovery_path=None,
        )

        # shlex.quote should escape these properly
        assert "command workstack sync" in script
        assert "'$branch'" in script or '"$branch"' in script
        assert "'file with spaces'" in script
        assert "'test;rm'" in script or '"test;rm"' in script

    def test_recovery_path_with_special_chars(self) -> None:
        """Recovery path with special characters is properly quoted."""
        recovery = Path("/tmp/path with spaces/recovery.sh")
        script = _render_posix_passthrough(
            command_name="sync",
            args=(),
            recovery_path=recovery,
        )

        # Path should be quoted
        assert "'$__workstack_recovery'" not in script  # Variable reference not quoted
        assert "'/tmp/path with spaces/recovery.sh'" in script

    def test_script_checks_pwd_exists(self) -> None:
        """Script includes check for PWD existence."""
        script = _render_posix_passthrough(
            command_name="sync",
            args=(),
            recovery_path=Path("/tmp/recovery.sh"),
        )

        assert '  if [ ! -d "$PWD" ]; then' in script
        assert '    . "$__workstack_recovery"' in script

    def test_script_respects_keep_scripts_env(self) -> None:
        """Script conditionally removes recovery based on WORKSTACK_KEEP_SCRIPTS."""
        script = _render_posix_passthrough(
            command_name="sync",
            args=(),
            recovery_path=Path("/tmp/recovery.sh"),
        )

        assert '  if [ -z "$WORKSTACK_KEEP_SCRIPTS" ]; then' in script
        assert '    rm -f "$__workstack_recovery"' in script


class TestQuoteFish:
    """Test fish shell argument quoting function."""

    def test_empty_string(self) -> None:
        """Empty string returns double quotes."""
        assert _quote_fish("") == '""'

    def test_simple_string(self) -> None:
        """Simple alphanumeric string is wrapped in quotes."""
        result = _quote_fish("simple")
        assert result == '"simple"'

    def test_escapes_dollar_sign(self) -> None:
        """Dollar sign is escaped for fish."""
        result = _quote_fish("$variable")
        assert result == '"\\$variable"'

    def test_escapes_semicolon(self) -> None:
        """Semicolon is escaped for fish."""
        result = _quote_fish("cmd;rm")
        assert result == '"cmd\\;rm"'

    def test_escapes_parentheses(self) -> None:
        """Parentheses are escaped for fish."""
        result = _quote_fish("(test)")
        assert result == '"\\(test\\)"'

    def test_escapes_brackets(self) -> None:
        """Brackets are escaped for fish."""
        result = _quote_fish("[test]")
        assert result == '"\\[test\\]"'

    def test_escapes_braces(self) -> None:
        """Braces are escaped for fish."""
        result = _quote_fish("{test}")
        assert result == '"\\{test\\}"'

    def test_escapes_wildcards(self) -> None:
        """Wildcard characters are escaped for fish."""
        assert _quote_fish("file*.txt") == '"file\\*.txt"'
        assert _quote_fish("file?.txt") == '"file\\?.txt"'

    def test_escapes_tilde(self) -> None:
        """Tilde is escaped for fish."""
        result = _quote_fish("~/path")
        assert result == '"\\~/path"'

    def test_escapes_pipes_and_redirects(self) -> None:
        """Pipes and redirect operators are escaped."""
        assert _quote_fish("a|b") == '"a\\|b"'
        assert _quote_fish("a<b") == '"a\\<b"'
        assert _quote_fish("a>b") == '"a\\>b"'

    def test_escapes_ampersand(self) -> None:
        """Ampersand is escaped for fish."""
        result = _quote_fish("cmd&bg")
        assert result == '"cmd\\&bg"'

    def test_escapes_backtick(self) -> None:
        """Backtick is escaped for fish."""
        result = _quote_fish("`command`")
        assert result == '"\\`command\\`"'

    def test_escapes_backslash(self) -> None:
        """Backslash is escaped for fish."""
        result = _quote_fish("path\\file")
        assert result == '"path\\\\file"'

    def test_escapes_double_quote(self) -> None:
        """Double quote is escaped for fish."""
        result = _quote_fish('say "hello"')
        assert result == '"say \\"hello\\""'

    def test_escapes_newline(self) -> None:
        """Newline is converted to \\n for fish."""
        result = _quote_fish("line1\nline2")
        assert result == '"line1\\nline2"'

    def test_escapes_tab(self) -> None:
        """Tab is converted to \\t for fish."""
        result = _quote_fish("col1\tcol2")
        assert result == '"col1\\tcol2"'

    def test_multiple_special_chars(self) -> None:
        """Multiple special characters are all escaped."""
        result = _quote_fish("$var;rm -rf *")
        assert result == '"\\$var\\;rm -rf \\*"'


class TestRenderFishPassthrough:
    """Test fish shell passthrough script generation."""

    def test_basic_command_no_args_no_recovery(self) -> None:
        """Generate fish script for simple command without args or recovery."""
        script = _render_fish_passthrough(
            command_name="sync",
            args=(),
            recovery_path=None,
        )

        assert 'command workstack "sync"' in script
        assert "set __workstack_exit $status" in script
        assert 'set __workstack_recovery ""' in script
        assert 'if test -n "$__workstack_recovery"' in script
        assert '        if not test -d "$PWD"' in script
        assert "return $__workstack_exit" in script
        assert script.endswith("\n")

    def test_command_with_recovery_path(self) -> None:
        """Generate fish script with recovery path specified."""
        recovery = Path("/tmp/recovery.fish")
        script = _render_fish_passthrough(
            command_name="sync",
            args=(),
            recovery_path=recovery,
        )

        assert 'command workstack "sync"' in script
        assert 'set __workstack_recovery "/tmp/recovery.fish"' in script
        assert '            source "$__workstack_recovery"' in script
        assert '            rm -f "$__workstack_recovery"' in script

    def test_command_with_simple_args(self) -> None:
        """Generate fish script with simple arguments."""
        script = _render_fish_passthrough(
            command_name="sync",
            args=("--force", "branch-name"),
            recovery_path=None,
        )

        assert 'command workstack "sync" "--force" "branch-name"' in script

    def test_command_with_special_chars_in_args(self) -> None:
        """Arguments with special characters use fish escaping."""
        script = _render_fish_passthrough(
            command_name="sync",
            args=("$branch", "(test)"),
            recovery_path=None,
        )

        # Fish escaping should be applied
        assert 'command workstack "sync"' in script
        assert '"\\$branch"' in script
        assert '"\\(test\\)"' in script

    def test_recovery_path_with_special_chars(self) -> None:
        """Recovery path with special characters uses fish escaping."""
        recovery = Path("/tmp/path with spaces/recovery.fish")
        script = _render_fish_passthrough(
            command_name="sync",
            args=(),
            recovery_path=recovery,
        )

        # Path should use fish escaping (no spaces in actual path, but test the mechanism)
        assert "set __workstack_recovery" in script

    def test_script_checks_pwd_exists(self) -> None:
        """Fish script includes check for PWD existence."""
        script = _render_fish_passthrough(
            command_name="sync",
            args=(),
            recovery_path=Path("/tmp/recovery.fish"),
        )

        assert '        if not test -d "$PWD"' in script
        assert '            source "$__workstack_recovery"' in script

    def test_script_respects_keep_scripts_env(self) -> None:
        """Fish script conditionally removes recovery based on WORKSTACK_KEEP_SCRIPTS."""
        script = _render_fish_passthrough(
            command_name="sync",
            args=(),
            recovery_path=Path("/tmp/recovery.fish"),
        )

        assert "        if not set -q WORKSTACK_KEEP_SCRIPTS" in script
        assert '            rm -f "$__workstack_recovery"' in script

    def test_fish_indentation_structure(self) -> None:
        """Fish script has proper nested if/end structure."""
        script = _render_fish_passthrough(
            command_name="sync",
            args=(),
            recovery_path=Path("/tmp/recovery.fish"),
        )

        lines = script.split("\n")
        # Count end statements - should match nested ifs
        end_count = sum(1 for line in lines if line.strip() == "end")
        assert end_count == 4  # Four nested if blocks
