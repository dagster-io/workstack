"""Shared constants for erk CLI commands."""

# GitHub issue label for erk plans
ERK_PLAN_LABEL = "erk-plan"

# GitHub Actions workflow for remote implementation dispatch
# Uncomment ONE option below (comment out others):

# Option 1: Pure git, single job (DEFAULT - no Graphite dependency, simpler)
DISPATCH_WORKFLOW_NAME = "dispatch-erk-queue-git.yml"
DISPATCH_WORKFLOW_METADATA_NAME = "dispatch-erk-queue-git"

# Option 2: Graphite CLI, multi-job (complex, use when Graphite stacks critical)
# DISPATCH_WORKFLOW_NAME = "dispatch-erk-queue.yml"
# DISPATCH_WORKFLOW_METADATA_NAME = "dispatch-erk-queue"

# Option 3: Graphite CLI, single job (Graphite dependency, simpler than multi-job)
# DISPATCH_WORKFLOW_NAME = "dispatch-erk-queue-single-job.yml"
# DISPATCH_WORKFLOW_METADATA_NAME = "dispatch-erk-queue-single-job"
