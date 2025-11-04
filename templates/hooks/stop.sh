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

# Session tracking reminder - let chronicle-assistant-guide skill handle this
checklist+="❓ Session tracking: Use chronicle-assistant-guide skill
   💡 The chronicle-assistant-guide skill provides complete workflow guidance
"

# Add TDD reminder (always show)
checklist+="
🧪 Did you write tests first? (TDD red-green-refactor)
"

# Add search reminder (always show)
checklist+="
🔍 Did you search Chronicle first?
   💡 Use chronicle-context-retriever skill: 'How did I implement X last time?'
   ⚡ 2,700x ROI - 1 second vs 20 minutes
"

checklist+="
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Output the checklist
output_message "$checklist"

exit 0