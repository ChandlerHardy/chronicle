#!/bin/bash

# Chronicle UserPromptSubmit Hook
# Processes user prompts and injects skill recommendations and reminders

set -euo pipefail

# Read JSON input from stdin
input_json=$(cat)
user_prompt=$(echo "$input_json" | jq -r '.prompt // empty')

# Flag to track if specific skill has been triggered
skill_triggered=false

# Array to track all checks performed (for debug output)
declare -a checks_performed=()

# Function to output JSON with system message and reasoning
output_context() {
    local message="$1"
    local reasoning="$2"
    local trigger="$3"

    # Create detailed output with reasoning
    local detailed_reason="🤔 HOOK REASONING:
Trigger: $trigger
Analysis: $reasoning
Decision: Inject skill recommendation

📋 Context: $message"

    # Set flag that a specific skill has been triggered
    skill_triggered=true

    jq -n \
        --arg msg "$message" \
        --arg reason "$detailed_reason" \
        '{
            "decision": "approve",
            "reason": $reason,
            "systemMessage": $msg
        }'
}

# Function to output debug reasoning when nothing triggered
output_debug_reasoning() {
    local prompt_preview="${user_prompt:0:60}"
    if [[ ${#user_prompt} -gt 60 ]]; then
        prompt_preview="${prompt_preview}..."
    fi

    # Build checks summary with actual newlines (like stop.sh does)
    local checks_summary="🔍 HOOK ANALYSIS (Debug Mode)

Prompt: \"${prompt_preview}\"

Checks performed:
"
    for check in "${checks_performed[@]}"; do
        checks_summary+="${check}
"
    done

    checks_summary+="
Decision: Approve without injection (no triggers matched)"

    # Include in BOTH reason (for logging) and systemMessage (for display)
    jq -n \
        --arg reason "$checks_summary" \
        --arg msg "$checks_summary" \
        '{
            "decision": "approve",
            "reason": $reason,
            "systemMessage": $msg
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

⚠️ Before implementing, use chronicle-context-retriever skill:
'How did I implement X last time?' or 'What was the blocker with Y?'

WHY: 2,700x ROI - 1 second vs 20 minutes
Proof: Sessions 21, 30, 31 show reinventing wastes time" \
                "User prompt contains implementation keywords but no search/reading keywords. Pattern matches development work that should first check Chronicle for prior implementations to avoid reinventing solutions." \
                "Implementation keywords detected (no config file)"
            exit 0
        fi
    fi
    exit 0
fi

# TDD skill triggers (highest priority - 95)
tdd_phrases="(let'?s (implement|add|build|write|create|fix|debug|resolve)|yeah let'?s (implement|add|build|write|create|fix|debug|resolve)|(I want|we should|can you)( to)? (implement|add|build|write|create|fix|debug|resolve)|(write|add|create) (a |the |some )?(function|class|method|feature|code))"
tdd_excludes="(test|write.*test|TDD|red-green-refactor|what (does|is)|how (does|do)|show me|explain)"

if echo "$user_prompt" | grep -iqE "$tdd_phrases"; then
    if ! echo "$user_prompt" | grep -iqE "$tdd_excludes"; then
        checks_performed+=("✅ 🧪 TDD patterns - MATCHED (implement/build/write keywords found, no test exclusions)")
        output_context "🚨 REQUIRED ACTION: TDD Skill Must Be Used

YOU MUST use the test-driven-development skill before writing any implementation code.

Required steps:
1. Write a failing test FIRST
2. Watch it fail (RED)
3. Write minimal code to pass (GREEN)
4. Refactor if needed

🎯 MANDATORY: Use Skill(command=\"test-driven-development\")

This is not optional. No exceptions." \
        "User prompt contains TDD trigger patterns (implement/build/write/create) but no test-related exclusions. This indicates new implementation work that violates TDD principles. According to TDD skill: 'NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST' - this is a red flag requiring immediate intervention." \
        "TDD violation detected"
        exit 0
    else
        checks_performed+=("⚪ 🧪 TDD patterns - no violation (keywords found but excluded: test-related context)")
    fi
else
    checks_performed+=("⚪ 🧪 TDD patterns - no match (no implement/build/write keywords)")
fi

# Other skill triggers with priorities
if echo "$user_prompt" | grep -iqE "(document session|export.*to obsidian|save.*to (vault|obsidian)|create (note|obsidian note) for)"; then
    checks_performed+=("✅ 📝 Obsidian export - MATCHED (document/export keywords found)")
    output_context "🚨 REQUIRED ACTION: Use chronicle-session-documenter Skill

Your prompt requires the chronicle-session-documenter skill.

This skill automates:
- Fetching session summary from Chronicle
- Creating structured Obsidian notes
- Adding metadata, wikilinks, and tags

🎯 MANDATORY: Use Skill(command=\"chronicle-session-documenter\")

You must run this skill before proceeding. No exceptions." \
        "User prompt contains keywords related to Obsidian export and session documentation. Pattern matches workflow for saving Chronicle sessions to knowledge base, which should be automated rather than done manually." \
        "Obsidian export detected"
    exit 0
else
    checks_performed+=("⚪ 📝 Obsidian export - no match (no document/export/vault keywords)")
fi

if echo "$user_prompt" | grep -iqE "(how did (I|we) (implement|fix|build|create|handle|solve)|what did (I|we) do (yesterday|last week|last month|before)|show me (all |past |previous )?work on|what was the blocker|when did (I|we) work on|find sessions? (about|on|for)|search (for |past )?sessions?)"; then
    checks_performed+=("✅ 🔍 Context retrieval - MATCHED (how did I/what did I/past work patterns found)")
    output_context "🚨 REQUIRED ACTION: Use chronicle-context-retriever Skill

Your prompt requires searching past development sessions.

This skill provides:
- Search Chronicle database for relevant sessions
- Retrieve detailed context from past work
- Find similar problems and solutions
- Recall previous decisions and rationale

🎯 MANDATORY: Use Skill(command=\"chronicle-context-retriever\")

You must run this skill before proceeding. No exceptions." \
        "User prompt contains context retrieval patterns (how did I/what did I/show me past work). This indicates need for historical development context which should be retrieved via specialized skill rather than manual searching." \
        "Context retrieval request"
    exit 0
else
    checks_performed+=("⚪ 🔍 Context retrieval - no match (no 'how did I' or past work patterns)")
fi

if echo "$user_prompt" | grep -iqE "(what'?s next|show (me )?(the )?roadmap|what should (I|we) work on|plan (new |a )?feature|create (a )?milestone|mark.*(milestone|step).*complete|what'?s in progress|view (the )?milestones?|track progress)"; then
    checks_performed+=("✅ 📊 Project tracking - MATCHED (roadmap/milestone/what's next keywords found)")
    output_context "🚨 REQUIRED ACTION: Use chronicle-project-tracker Skill

Your prompt requires project planning and tracking.

This skill manages:
- Database-tracked milestones
- Next steps and TODOs
- Roadmap visualization
- Progress reports
- Session-to-milestone linking

🎯 MANDATORY: Use Skill(command=\"chronicle-project-tracker\")

You must run this skill before proceeding. No exceptions." \
        "User prompt contains project management keywords (roadmap/milestone/what's next/progress). This indicates planning or tracking work that should use the specialized project tracking system rather than ad-hoc management." \
        "Project tracking request"
    exit 0
else
    checks_performed+=("⚪ 📊 Project tracking - no match (no roadmap/milestone keywords)")
fi

# Basic Chronicle Advocate search reminder (only if no specific skill triggered)
if [[ "$skill_triggered" == "false" ]]; then
    if echo "$user_prompt" | grep -iqE "(implement|add|create|build|fix|debug)"; then
        if ! echo "$user_prompt" | grep -iqE "(read|view|show|explain)"; then
            checks_performed+=("✅ ⚙️ General implementation - MATCHED (implement/add/create keywords, no read/view exclusions)")
            output_context "🚨 REQUIRED ACTION: Use chronicle-context-retriever Skill

Before implementing anything, you MUST search Chronicle for prior art.

Ask questions like:
'How did I implement X last time?' or 'What was the blocker with Y?'

🎯 MANDATORY: Use Skill(command=\"chronicle-context-retriever\")

WHY: 2,700x ROI - 1 second vs 20 minutes
Proof: Sessions 21, 30, 31 show reinventing wastes time

You must run this skill before proceeding. No exceptions." \
                    "General implementation keywords detected without specific skill matches. Default behavior: recommend Chronicle search to avoid reinventing solutions and leverage prior work." \
                    "General implementation detected"
            exit 0
        else
            checks_performed+=("⚪ ⚙️ General implementation - has exclusions (implementation keywords found but excluded: read/view/show/explain)")
        fi
    else
        checks_performed+=("⚪ ⚙️ General implementation - no match (no implement/add/create keywords)")
    fi
fi

# No triggers matched - output debug reasoning
output_debug_reasoning
exit 0