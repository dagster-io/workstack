#!/usr/bin/env python3
"""
Download all GitHub discussions from python-code-smells-and-anti-patterns category.

This is a one-time script designed to download discussions from dagster-io/internal
repository and persist them as markdown files in docs/reference/dagster-discussions/.

CRITICAL: Not designed for reusability or incremental updates. Will fail on existing files.
"""

import json
import re
import subprocess
import unicodedata
from pathlib import Path

OWNER = "dagster-io"
REPO = "internal"
CATEGORY_NAME = "Python Code Smells and Anti-Patterns"
OUTPUT_DIR = Path("docs/reference/dagster-discussions")


def run_gh_graphql(
    query: str, variables: dict[str, str] | None = None, paginate: bool = False
) -> dict:
    """
    Execute GitHub GraphQL query using gh CLI.

    CRITICAL: Requires -H 'GraphQL-Features: discussions_api' header for discussions.
    """
    cmd = [
        "gh",
        "api",
        "graphql",
        "-H",
        "GraphQL-Features: discussions_api",
        "-f",
        f"query={query}",
    ]

    if variables:
        for key, value in variables.items():
            cmd.extend(["-f", f"{key}={value}"])

    if paginate:
        cmd.append("--paginate")

    result = subprocess.run(cmd, check=True, capture_output=True, text=True, encoding="utf-8")
    return json.loads(result.stdout)


def get_category_id(owner: str, repo: str, category_name: str) -> str:
    """
    Query repository for category ID by name.

    Returns: Category ID string (e.g., "DIC_kwDOAbCdEf4B9g8h")
    Raises: SystemExit if category not found
    """
    query = """
    query($owner: String!, $repo: String!) {
      repository(owner: $owner, name: $repo) {
        discussionCategories(first: 25) {
          nodes {
            id
            name
          }
        }
      }
    }
    """

    response = run_gh_graphql(query, {"owner": owner, "repo": repo})
    categories = response["data"]["repository"]["discussionCategories"]["nodes"]

    for category in categories:
        if category["name"] == category_name:
            return category["id"]

    raise SystemExit(f"Error: Category '{category_name}' not found in {owner}/{repo}")


def list_discussions(owner: str, repo: str, category_id: str) -> list[dict]:
    """
    List all discussions in the specified category.

    Uses --paginate for automatic cursor-based pagination.
    Returns: List of discussion metadata dictionaries
    """
    query = """
    query($owner: String!, $repo: String!, $categoryId: ID!, $endCursor: String) {
      repository(owner: $owner, name: $repo) {
        discussions(first: 100, categoryId: $categoryId, after: $endCursor) {
          pageInfo {
            hasNextPage
            endCursor
          }
          nodes {
            number
            title
            body
            author {
              login
            }
            createdAt
            updatedAt
            url
          }
        }
      }
    }
    """

    response = run_gh_graphql(
        query, {"owner": owner, "repo": repo, "categoryId": category_id}, paginate=True
    )

    return response["data"]["repository"]["discussions"]["nodes"]


def sanitize_title(title: str) -> str:
    """
    Convert discussion title to kebab-case filename.

    - Lowercase conversion
    - Replace spaces with hyphens
    - Remove special characters (keep alphanumeric and hyphens)
    - Unicode normalization (NFC), remove emojis
    - Strip trailing hyphens/slashes

    Returns: Sanitized filename string (without .md extension)
    Fallback: Empty string if title becomes empty after sanitization
    """
    # Unicode normalization
    normalized = unicodedata.normalize("NFC", title)

    # Remove emojis and non-ASCII characters that aren't alphanumeric
    ascii_title = normalized.encode("ascii", "ignore").decode("ascii")

    # Lowercase
    lower = ascii_title.lower()

    # Replace spaces with hyphens
    with_hyphens = lower.replace(" ", "-")

    # Keep only alphanumeric and hyphens
    cleaned = re.sub(r"[^a-z0-9-]", "", with_hyphens)

    # Remove multiple consecutive hyphens
    deduplicated = re.sub(r"-+", "-", cleaned)

    # Strip leading/trailing hyphens
    stripped = deduplicated.strip("-")

    return stripped


def generate_markdown(discussion: dict, category_name: str) -> str:
    """
    Generate markdown file with YAML frontmatter.

    Frontmatter fields:
    - discussion_number
    - title
    - author
    - created_at
    - updated_at
    - url
    - category

    Body: Original discussion body in markdown
    """
    number = discussion["number"]
    title = discussion["title"]
    author = discussion["author"]["login"]
    created_at = discussion["createdAt"]
    updated_at = discussion["updatedAt"]
    url = discussion["url"]
    body = discussion["body"]

    frontmatter = f"""---
discussion_number: {number}
title: "{title}"
author: {author}
created_at: {created_at}
updated_at: {updated_at}
url: {url}
category: {category_name}
---

"""

    return frontmatter + body


def create_index(discussions: list[dict], output_dir: Path) -> None:
    """
    Generate README.md index file with list of all discussions.

    Includes:
    - Discussion number
    - Title
    - Author
    - Link to discussion file (relative path)
    """
    index_lines = [
        "# Dagster Discussions: Python Code Smells and Anti-Patterns",
        "",
        "Downloaded discussions from dagster-io/internal repository.",
        "",
        "## Discussions",
        "",
    ]

    # Sort by discussion number
    sorted_discussions = sorted(discussions, key=lambda d: d["number"])

    for discussion in sorted_discussions:
        number = discussion["number"]
        title = discussion["title"]
        author = discussion["author"]["login"]
        sanitized = sanitize_title(title)

        # Fallback to number-only filename if sanitization produces empty string
        if sanitized:
            filename = f"{number}-{sanitized}.md"
        else:
            filename = f"{number}.md"

        index_lines.append(f"- **#{number}**: [{title}](./{filename}) (by @{author})")

    index_content = "\n".join(index_lines) + "\n"
    index_path = output_dir / "README.md"
    index_path.write_text(index_content, encoding="utf-8")


def main() -> None:
    """
    Main download orchestration logic.

    CRITICAL: Fail immediately on any error - no partial downloads or retries.
    """
    # Step 1: Get category ID
    print(f"Finding category ID for '{CATEGORY_NAME}'...")
    category_id = get_category_id(OWNER, REPO, CATEGORY_NAME)
    print(f"Found category ID: {category_id}")

    # Step 2: List all discussions
    print(f"Fetching discussions from {OWNER}/{REPO}...")
    discussions = list_discussions(OWNER, REPO, category_id)
    print(f"Found {len(discussions)} discussions")

    # Step 3: Download each discussion
    print(f"Writing discussions to {OUTPUT_DIR}/...")
    for discussion in discussions:
        number = discussion["number"]
        title = discussion["title"]
        sanitized = sanitize_title(title)

        # Fallback to number-only filename if sanitization produces empty string
        if sanitized:
            filename = f"{number}-{sanitized}.md"
        else:
            filename = f"{number}.md"

        filepath = OUTPUT_DIR / filename

        # Generate markdown content
        markdown_content = generate_markdown(discussion, CATEGORY_NAME)

        # Write to file (will fail if file exists)
        filepath.write_text(markdown_content, encoding="utf-8")
        print(f"  ✓ {filename}")

    # Step 4: Create index
    print("Creating index file...")
    create_index(discussions, OUTPUT_DIR)
    print("  ✓ README.md")

    print(f"\n✅ Successfully downloaded {len(discussions)} discussions to {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
