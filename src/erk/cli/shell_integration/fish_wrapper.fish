# Erk shell integration for fish
# This function wraps the erk CLI to provide seamless worktree switching

function erk
    # Don't intercept if we're doing shell completion
    if set -q _ERK_COMPLETE
        command erk $argv
        return
    end

    set -l script_path (env ERK_SHELL=fish command erk __shell $argv)
    set -l exit_status $status

    # Passthrough mode
    if test "$script_path" = "__ERK_PASSTHROUGH__"
        command erk $argv
        return
    end

    # If __shell returned non-zero, error messages are already sent to stderr
    if test $exit_status -ne 0
        return $exit_status
    end

    # Source the script file if it exists
    if test -n "$script_path" -a -f "$script_path"
        source "$script_path"
        set -l source_exit $status

        # Clean up unless ERK_KEEP_SCRIPTS is set
        if not set -q ERK_KEEP_SCRIPTS
            rm -f "$script_path"
        end

        return $source_exit
    end
end
