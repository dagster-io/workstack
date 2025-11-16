# Erk shell integration for zsh
# This function wraps the erk CLI to provide seamless worktree switching

erk() {
  # Don't intercept if we're doing shell completion
  [ -n "$_ERK_COMPLETE" ] && { command erk "$@"; return; }

  local script_path exit_status
  script_path=$(ERK_SHELL=zsh command erk __shell "$@")
  exit_status=$?

  # Passthrough mode: run the original command directly
  [ "$script_path" = "__ERK_PASSTHROUGH__" ] && { command erk "$@"; return; }

  # If __shell returned non-zero, error messages are already sent to stderr
  [ $exit_status -ne 0 ] && return $exit_status

  # Source the script file if it exists
  if [ -n "$script_path" ] && [ -f "$script_path" ]; then
    source "$script_path"
    local source_exit=$?

    # Clean up unless ERK_KEEP_SCRIPTS is set
    if [ -z "$ERK_KEEP_SCRIPTS" ]; then
      rm -f "$script_path"
    fi

    return $source_exit
  fi
}
