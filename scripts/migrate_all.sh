#!/bin/bash
# Migrate all remaining test files

files=(
    "tests/commands/graphite/test_land_stack.py"
    "tests/commands/graphite/test_gt_tree_formatting.py"
    "tests/unit/fakes/test_fake_graphite_ops.py"
    "tests/commands/navigation/test_up.py"
    "tests/core/operations/test_graphite_ops.py"
    "tests/commands/display/test_tree.py"
    "tests/commands/display/list/test_stacks.py"
    "tests/commands/display/list/test_root_filtering.py"
    "tests/commands/sync/test_sync.py"
    "tests/commands/navigation/test_switch_up_down.py"
    "tests/commands/navigation/test_down.py"
    "tests/commands/display/list/test_basic.py"
    "tests/test_utils/repo_setup.py"
    "tests/unit/status/test_graphite_stack_collector.py"
    "tests/commands/workspace/test_create.py"
)

for file in "${files[@]}"; do
    echo "Migrating $file..."
    python scripts/migrate_branch_metadata.py "$file"
done

echo ""
echo "✅ Migration complete!"
