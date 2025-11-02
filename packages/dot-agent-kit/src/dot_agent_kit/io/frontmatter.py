"""Frontmatter parsing and injection."""

import re

import yaml

from dot_agent_kit.models import ArtifactFrontmatter

FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL | re.MULTILINE)


def validate_frontmatter(frontmatter: ArtifactFrontmatter) -> list[str]:
    """Validate frontmatter structure and return errors."""
    errors: list[str] = []

    # Validate kit_id format (kebab-case)
    if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", frontmatter.kit_id):
        errors.append(f"Invalid kit_id format: {frontmatter.kit_id}")

    # Validate version format (semver-ish)
    if not re.match(r"^\d+\.\d+\.\d+", frontmatter.kit_version):
        errors.append(f"Invalid version format: {frontmatter.kit_version}")

    # Validate artifact_type
    valid_types = {"agent", "command", "skill"}
    if frontmatter.artifact_type not in valid_types:
        errors.append(
            f"Invalid artifact_type: {frontmatter.artifact_type} (must be one of {valid_types})"
        )

    return errors


def parse_frontmatter(content: str) -> ArtifactFrontmatter | None:
    """Extract frontmatter from markdown content."""
    match = FRONTMATTER_PATTERN.search(content)
    if not match:
        return None

    yaml_content = match.group(1)
    data = yaml.safe_load(yaml_content)

    # Extract from __dot_agent nested key
    if "__dot_agent" not in data:
        return None

    dot_agent = data["__dot_agent"]

    return ArtifactFrontmatter(
        kit_id=dot_agent["kit_id"],
        kit_version=dot_agent["kit_version"],
        artifact_type=dot_agent["artifact_type"],
        artifact_path=dot_agent["artifact_path"],
    )


def add_frontmatter(content: str, frontmatter: ArtifactFrontmatter) -> str:
    """Add frontmatter to markdown content, preserving existing fields."""
    # Check if content already has frontmatter
    match = FRONTMATTER_PATTERN.search(content)
    existing_fields = {}
    content_without_fm = content

    if match:
        # Parse existing frontmatter
        yaml_content = match.group(1)
        existing_fields = yaml.safe_load(yaml_content) or {}
        # Remove existing frontmatter from content
        content_without_fm = FRONTMATTER_PATTERN.sub("", content, count=1)

    # Remove __dot_agent if it exists in existing fields to avoid duplication
    if "__dot_agent" in existing_fields:
        del existing_fields["__dot_agent"]

    # Add __dot_agent metadata
    existing_fields["__dot_agent"] = {
        "kit_id": frontmatter.kit_id,
        "kit_version": frontmatter.kit_version,
        "artifact_type": frontmatter.artifact_type,
        "artifact_path": frontmatter.artifact_path,
    }

    # Generate YAML with existing fields first, then __dot_agent
    fm_yaml = yaml.dump(
        existing_fields,
        default_flow_style=False,
        sort_keys=False,
    )

    fm_block = f"---\n{fm_yaml}---\n\n"
    return fm_block + content_without_fm.lstrip()
