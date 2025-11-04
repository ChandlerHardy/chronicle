#!/bin/bash

# Chronicle PostToolUse Hook
# Tracks edited files for future build checking

set -euo pipefail

# Read JSON input from stdin
input_json=$(cat)

# Get script directory and log file
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$SCRIPT_DIR/../edit-log.txt"

# Get current timestamp
timestamp=$(date '+%Y-%m-%d %H:%M:%S')

# Extract relevant information from the hook input
if echo "$input_json" | jq -e '.toolInvocations[0]' >/dev/null 2>&1; then
    # Parse tool invocations if available
    tool_info=$(echo "$input_json" | jq -r '.toolInvocations[0] // empty')
    tool_name=$(echo "$tool_info" | jq -r '.name // "unknown"')

    if [[ "$tool_name" != "unknown" ]]; then
        # Log the tool usage with timestamp
        echo "[$timestamp] Tool: $tool_name" >> "$LOG_FILE"

        # If it's a file editing tool, we could extract file paths in the future
        case "$tool_name" in
            "Edit"|"Write"|"NotebookEdit")
                # Future enhancement: extract file paths and track for builds
                echo "[$timestamp] File edit detected: $tool_name" >> "$LOG_FILE"
                ;;
        esac
    fi
fi

# Exit silently (PostToolUse hooks should not produce output for user)
exit 0