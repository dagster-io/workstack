"""Create command subpackage.

Handles all variants of worktree creation:
- Regular creation with optional Graphite integration
- Creation from existing branches
- Creation from current branch (move)
- Creation with plan files
- Creation with .plan/ folder copying
"""

from workstack.cli.commands.create.orchestrator import create as create
from workstack.cli.commands.create.post_creation import make_env_content as make_env_content
