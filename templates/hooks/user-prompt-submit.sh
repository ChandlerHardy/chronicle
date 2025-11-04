#!/bin/bash

# Chronicle UserPromptSubmit Hook
# Processes user prompts and injects skill recommendations and reminders

set -euo pipefail

# Read JSON input from stdin
input_json=$(cat)
user_prompt=$(echo "$input_json" | jq -r '.user_prompt // empty')

# Function to output JSON with additional context
output_context() {
    local message="$1"
    jq -n \
        --arg msg "$message" \
        '{
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": $msg
            }
        }'
}

# Get script directory - note: when run from ~/.claude/hooks/, we need to find Chronicle project
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Chronicle is a global tool - prioritize global configuration
if [[ -f "$HOME/.claude/config/skill-rules.json" ]]; then
    # Primary: Global config (installed by setup-hooks)
    CONFIG_FILE="$HOME/.claude/config/skill-rules.json"
elif [[ -f "/Users/chandlerhardy/repos/chronicle/templates/skill-rules.json" ]]; then
    # Fallback: Chronicle repo templates (for development)
    CONFIG_FILE="/Users/chandlerhardy/repos/chronicle/templates/skill-rules.json"
else
    # Final fallback - search from current directory
    PROJECT_ROOT="$(pwd)"
    while [[ "$PROJECT_ROOT" != "/" ]] && [[ ! -f "$PROJECT_ROOT/templates/skill-rules.json" ]]; do
        PROJECT_ROOT="$(dirname "$PROJECT_ROOT")"
    done
    CONFIG_FILE="$PROJECT_ROOT/templates/skill-rules.json"
fi

# Check if skill rules config exists
if [[ ! -f "$CONFIG_FILE" ]]; then
    # Fallback to basic search reminder
    if echo "$user_prompt" | grep -iqE "(implement|add|create|build|fix|debug|write|can't believe|why (isn't|doesn't|won't|can't)|this should|I (want|need) to (build|add|implement|create)|let's (build|add|implement|create))"; then
        if ! echo "$user_prompt" | grep -iqE "(read|view|show|explain|what is|search.*chronicle|mcp__chronicle)"; then
            output_context "🔍 SEARCH CHRONICLE FIRST

⚠️ Before implementing, run:
mcp__chronicle__search_sessions(query=\"relevant keywords\")

WHY: 2,700x ROI - 1 second vs 20 minutes
Proof: Sessions 21, 30, 31 show reinventing wastes time"
            exit 0
        fi
    fi
    exit 0
fi

# TDD skill triggers (highest priority - 95)
tdd_phrases="(let'?s (implement|add|build|write|create)|yeah let'?s (implement|add|build|write|create)|(I want|we should|can you)( to)? (implement|add|build|write|create)|(write|add|create) (a |the |some )?(function|class|method|feature|code))"
tdd_excludes="(test|write.*test|TDD|red-green-refactor|what (does|is)|how (does|do)|show me|explain)"

if echo "$user_prompt" | grep -iqE "$tdd_phrases"; then
    if ! echo "$user_prompt" | grep -iqE "$tdd_excludes"; then
        output_context "🧪 TDD ENFORCER ACTIVATED

Before writing implementation code, we MUST:

1. Write a failing test FIRST
2. Watch it fail (RED)
3. Write minimal code to pass (GREEN)
4. Refactor if needed

No exceptions. The test-driven-development skill has comprehensive guidance.

Load with: Skill(command=\"test-driven-development\")"
        exit 0
    fi
fi

# Other skill triggers with priorities
if echo "$user_prompt" | grep -iqE "(document session|export.*to obsidian|save.*to (vault|obsidian)|create (note|obsidian note) for)"; then
    output_context "🎯 SKILL DETECTED: chronicle-session-documenter

Your prompt matches documenting sessions to Obsidian vault.

This skill automates:
- Fetching session summary from Chronicle
- Creating structured Obsidian notes
- Adding metadata, wikilinks, and tags

Load with: Skill(command=\"chronicle-session-documenter\")"
    exit 0
fi

if echo "$user_prompt" | grep -iqE "(how did (I|we) (implement|fix|build|create|handle|solve)|what did (I|we) do (yesterday|last week|last month|before)|show me (all |past |previous )?work on|what was the blocker|when did (I|we) work on|find sessions? (about|on|for)|search (for |past )?sessions?)"; then
    output_context "🔍 SKILL DETECTED: chronicle-context-retriever

Your prompt matches searching past development sessions.

This skill helps:
- Search Chronicle database for relevant sessions
- Retrieve detailed context from past work
- Find similar problems and solutions
- Recall previous decisions and rationale

Load with: Skill(command=\"chronicle-context-retriever\")"
    exit 0
fi

if echo "$user_prompt" | grep -iqE "(what'?s next|show (me )?(the )?roadmap|what should (I|we) work on|plan (new |a )?feature|create (a )?milestone|mark.*(milestone|step).*complete|what'?s in progress|view (the )?milestones?|track progress)"; then
    output_context "📊 SKILL DETECTED: chronicle-project-tracker

Your prompt matches project planning and tracking.

This skill manages:
- Database-tracked milestones
- Next steps and TODOs
- Roadmap visualization
- Progress reports
- Session-to-milestone linking

Load with: Skill(command=\"chronicle-project-tracker\")"
    exit 0
fi

# Basic Chronicle Advocate search reminder
if echo "$user_prompt" | grep -iqE "(implement|add|create|build|fix|debug)"; then
    if ! echo "$user_prompt" | grep -iqE "(read|view|show|explain)"; then
        output_context "🔍 SEARCH CHRONICLE FIRST

⚠️ Before implementing, run:
mcp__chronicle__search_sessions(query=\"relevant keywords\")

WHY: 2,700x ROI - 1 second vs 20 minutes
Proof: Sessions 21, 30, 31 show reinventing wastes time"
    fi
fi

exit 0