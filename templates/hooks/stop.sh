#!/bin/bash

# Chronicle Stop Hook
# Post-response quality checks and reminders

set -euo pipefail

# Read JSON input from stdin
input_json=$(cat)

# Function to output messages to Claude
output_message() {
    local message="$1"
    jq -n \
        --arg msg "$message" \
        '{
            "hookSpecificOutput": {
                "hookEventName": "Stop",
                "additionalContext": $msg
            }
        }'
}

# Build quality checklist
checklist="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 QUALITY SELF-CHECK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"

# Check session tracking - try MCP call directly with error handling
session_status=$(mcp__chronicle__get_current_session 2>/dev/null || echo '{"active": false}')
if echo "$session_status" | jq -r '.active // false' 2>/dev/null | grep -q true; then
    checklist+="✅ Session tracking: Active\n"
elif echo "$session_status" | jq -e '.error' 2>/dev/null >/dev/null; then
    # MCP tool exists but returned an error
    checklist+="⚠️  Session tracking error (MCP issue)
   💡 Tip: Check MCP server status
"
else
    # MCP tool not available or other issue
    checklist+="❓ Session tracking: Not checked
   💡 Tip: Run 'chronicle start claude' to track work
"
fi

# Add TDD reminder (always show)
checklist+="
🧪 Did you write tests first? (TDD red-green-refactor)
"

# Add search reminder (always show)
checklist+="
🔍 Did you search Chronicle first?
   💡 Try: mcp__chronicle__search_sessions(query=\"...\")
   ⚡ 2,700x ROI - 1 second vs 20 minutes
"

checklist+="
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Output the checklist
output_message "$checklist"

exit 0