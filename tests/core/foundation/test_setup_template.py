from pathlib import Path

from workstack.core.init_utils import render_config_template


def _get_presets_dir() -> Path:
    """Get the path to the presets directory."""
    # Navigate from tests/core/foundation to src/workstack/cli/presets
    return Path(__file__).parent.parent.parent.parent / "src" / "workstack" / "cli" / "presets"


def test_render_config_template_default() -> None:
    presets_dir = _get_presets_dir()
    content = render_config_template(presets_dir, preset=None)
    assert "[env]" in content
    assert "[post_create]" in content
    # Contains helpful comments
    assert "EXAMPLE_KEY" in content


def test_render_config_template_dagster() -> None:
    presets_dir = _get_presets_dir()
    content = render_config_template(presets_dir, "dagster")
    assert "DAGSTER_GIT_REPO_DIR" in content
    assert "commands = [" in content
    assert "uv venv" in content
    assert "uv run make dev_install" in content
