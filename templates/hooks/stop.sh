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

# Check if we have access to mcp__chronicle tools
can_check_session=false
if command -v mcp__chronicle__get_current_session >/dev/null 2>&1; then
    can_check_session=true
fi

# Build quality checklist
checklist="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 QUALITY SELF-CHECK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"

# Check session tracking
if [[ "$can_check_session" == true ]]; then
    session_status=$(mcp__chronicle__get_current_session 2>/dev/null || echo '{"active": false}')
    if echo "$session_status" | jq -r '.active // false' | grep -q true; then
        checklist+="✅ Session tracking: Active\n"
    else
        checklist+="⚠️  Not in tracked Chronicle session
   💡 Tip: Run 'chronicle start claude' to track this work
"
    fi
else
    checklist+="❓ Session tracking: Could not check (MCP unavailable)
   💡 Tip: Verify MCP server is running and accessible"
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