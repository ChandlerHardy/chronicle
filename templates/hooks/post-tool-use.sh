#!/bin/bash

# Chronicle PostToolUse Hook
# Tracks edited files and enforces skills over MCP tools

set -euo pipefail

# Read JSON input from stdin
input_json=$(cat)

# Get script directory and log file
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$SCRIPT_DIR/../edit-log.txt"

# Get current timestamp
timestamp=$(date '+%Y-%m-%d %H:%M:%S')

# Function to output skill recommendations
output_skill_recommendation() {
    local message="$1"
    jq -n \
        --arg msg "$message" \
        '{
            "decision": "approve",
            "reason": $msg,
            "systemMessage": $msg
        }'
}

# Extract relevant information from the hook input
tool_name=$(echo "$input_json" | jq -r '.tool_name // "unknown"')

if [[ "$tool_name" != "unknown" ]]; then
    # Log the tool usage with timestamp
    echo "[$timestamp] Tool: $tool_name" >> "$LOG_FILE"

    # Check for MCP tools that should have used skills instead
    case "$tool_name" in
        "mcp__chronicle__search_sessions"|"mcp__chronicle__get_session_summary"|"mcp__chronicle__get_current_session")
            # These Chronicle MCP tools should use skills instead
            recommendation="⚠️ SKILLS PREFERRED OVER MCP TOOLS

You used $tool_name - consider using skills instead:

🔍 For searching past sessions: Use chronicle-context-retriever skill
   - Complete workflow guidance
   - Better context extraction
   - Structured output with examples

📊 For project tracking: Use chronicle-project-tracker skill
   - Database-tracked milestones
   - Roadmap visualization

🔄 For Chronicle workflows: Use chronicle-workflow skill
   - Session tracking guidance
   - Best practices

📝 For documenting sessions: Use chronicle-session-documenter skill
   - Obsidian integration
   - Structured note creation

💡 Skills provide complete workflows, not just individual operations
💡 Skills work even when MCP server is unavailable (CLI fallback)
💡 Skills include best practices and error handling

Load skills with: Skill(command=\"skill-name\")"
            output_skill_recommendation "$recommendation"
            ;;
        "Edit"|"Write"|"NotebookEdit")
            echo "[$timestamp] File edit detected: $tool_name" >> "$LOG_FILE"
            ;;
    esac
fi

exit 0