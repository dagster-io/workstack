"""Plan commands moved to top-level.

All plan commands are now top-level:
- erk list (formerly erk plan list)
- erk get (formerly erk plan get)
- erk close (formerly erk plan close)
- erk retry (formerly erk plan retry)

The plan_group has been removed - no backward compatibility.
"""

# Individual command implementations remain in their original files:
# - close_cmd.py
# - get.py
# - list_cmd.py
# - retry_cmd.py
