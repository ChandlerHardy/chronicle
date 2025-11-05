# Chronicle Hooks System

> **Token-Efficient Workflow Automation**
>
> Replaces expensive always-active Chronicle Advocate agent (~400 tokens/message) with lightweight hooks (~50-150 tokens when needed). **50% reduction in token overhead** while maintaining same enforcement quality.

## Overview

Chronicle's hooks system automatically enforces best practices using Claude Code's native hooks API. Based on Reddit post best practices from a developer managing 300k+ LOC solo projects.

### Architecture

**3-Tier System:**

1. **Tier 1: Hooks** (50-150 tokens) - 90% of enforcement
   - UserPromptSubmit: Pre-prompt reminders
   - Stop: Post-response quality checks
   - PostToolUse: Edit tracking

2. **Tier 2: Skills** (500-1000 tokens) - Workflow guidance
   - Detailed procedures, only loaded when needed

3. **Tier 3: Agents** (Always loaded) - Deep analysis only
   - Chronicle Advocate: Manual launch for comprehensive analysis
   - TDD Advocate: Always active (test enforcement is critical)

## Hooks

### UserPromptSubmit Hook

**File:** `.claude/hooks/user-prompt-submit.sh`

**Purpose:** Inject "Search Chronicle First" reminder BEFORE Claude sees the prompt

**Triggers:**
- **Keywords:** implement, add, create, build, fix, debug, write
- **Phrases:** "can't believe", "why isn't", "this should", "I want to add"
- **Exclusions:** read, view, show, explain (read-only operations)

**Token cost:** ~50-100 tokens (just the injected message)

**Example:**
```
User: "I want to add a new export feature"
↓
Hook detects "add" keyword
↓
Injects before Claude sees it:
🔍 SEARCH CHRONICLE FIRST

⚠️ Before implementing, run:
mcp__chronicle__search_sessions(query="export")

WHY: 2,700x ROI - 1 second vs 20 minutes
Proof: Sessions 21, 30, 31
↓
Claude reads user prompt + reminder
Claude searches Chronicle before implementing
```

#### Skill Auto-Activation (Milestone #13)

**Added:** v6.1 (Milestone #13)

The UserPromptSubmit hook also detects when user prompts match Chronicle skill triggers and automatically recommends relevant skills.

**Supported Skills:**
- 🧪 **test-driven-development** (Priority 95) - TDD enforcement (superpowers skill)
- 🎯 **chronicle-session-documenter** (Priority 90) - Document sessions to Obsidian
- 🔍 **chronicle-context-retriever** (Priority 90) - Search past work
- 📊 **chronicle-project-tracker** (Priority 80) - Manage milestones and roadmap
- 🔄 **chronicle-workflow** (Priority 70) - Session workflow guidance
- 🌐 **chronicle-remote-summarizer** (Priority 60) - Remote session workflows
- 📚 **chronicle-assistant-guide** (Priority 50) - General Chronicle guidance

**How It Works:**

```
User: "document session 75 to Obsidian"
↓
Hook detects skill trigger:
  - Keyword: "document"
  - Phrase match: "document session"
↓
Injects skill recommendation:
🎯 SKILL DETECTED: chronicle-session-documenter

Your prompt matches documenting sessions to Obsidian vault.

This skill automates:
- Fetching session summary from Chronicle
- Creating structured Obsidian notes
- Adding metadata, wikilinks, and tags

Load with: Skill(command="chronicle-session-documenter")
↓
Claude sees recommendation and loads skill automatically
```

**Priority System:**

When multiple skills match the same prompt, the highest priority skill is recommended:

```
User: "how did I implement authentication?"
↓
Matches BOTH:
  - Chronicle Advocate (implement keyword)
  - chronicle-context-retriever (how did I pattern)
↓
Shows BOTH messages (combined with separator)
```

**Trigger Configuration:**

Each skill in `.claude/config/skill-rules.json` has:
- **keywords**: List of words that trigger the skill
- **phrases**: Regex patterns for specific phrases
- **excludes**: Patterns that prevent triggering (false positive prevention)
- **priority**: Number (higher = recommended first when multiple match)

**Example Configuration:**

```json
{
  "skillActivation": {
    "chronicle-session-documenter": {
      "priority": 90,
      "skillCommand": "chronicle-session-documenter",
      "triggers": {
        "keywords": [],
        "phrases": [
          "(?i)document session",
          "(?i)export.*to obsidian",
          "(?i)save.*to (vault|obsidian)"
        ],
        "excludes": ["document.*code", "documentation.*for"]
      },
      "message": "🎯 SKILL DETECTED: chronicle-session-documenter\n\n..."
    }
  }
}
```

**Benefits:**

- ✅ **Automatic discovery** - Skills activate when needed, no manual loading
- ✅ **Consistency** - Guaranteed use of best practices from skills
- ✅ **Token efficiency** - 50-100 tokens for recommendation vs 500-1000 for full skill
- ✅ **False positive prevention** - Exclusion patterns avoid irrelevant triggers
- ✅ **Priority system** - Highest priority skill wins when multiple match

**Testing:**

Comprehensive tests in `tests/test_hooks.py` cover:
- All 7 skill trigger patterns (37+ test cases)
- Exclusion patterns (false positive prevention)
- Priority system (multiple matches)
- Chronicle Advocate + skill combination
- Edge cases and JSON validation

See `tests/test_hooks.py` for examples.

#### TDD Skill Auto-Activation (Next Step #93)

**Added:** Session 99 (addresses Next Step #93)

The **test-driven-development** skill from superpowers marketplace now auto-activates when you start implementing code.

**Why TDD Skill over TDD Advocate Agent:**
- **15x cheaper**: 1,000 tokens/session (loaded once) vs 15,000 tokens/session (300 per message)
- **More comprehensive**: 365 lines of guidance vs 35 lines in agent
- **Better enforcement**: "Iron Law", red flags, rationalization counters
- **Smarter activation**: Only when implementing, not on every message

**Triggers:**
- "let's implement/add/build/write/create X"
- "yeah let's implement/add/build/write/create X"
- "I want/we should/can you (to) implement/add/build/write/create X"
- "write/add/create a function/class/method/feature/code"

**Exclusions:**
- Already writing tests ("write a test", "TDD", "red-green-refactor")
- Asking questions ("what does", "how does", "explain", "show me")

**Example:**
```
User: "let's implement the export feature"
↓
Hook injects:
🧪 TDD ENFORCER ACTIVATED

Before writing implementation code, we MUST:

1. Write a failing test FIRST
2. Watch it fail (RED)
3. Write minimal code to pass (GREEN)
4. Refactor if needed

No exceptions. The test-driven-development skill has comprehensive guidance.

Load with: Skill(command="test-driven-development")
```

**Benefits:**
- ✅ Catches TDD violations **before** code is written
- ✅ Loads comprehensive 365-line guidance (not just reminder)
- ✅ Has "delete and start over" enforcement
- ✅ Counters common rationalizations ("I'll test after", "too simple to test", etc.)
- ✅ 15x cheaper than always-active agent

**Note:** CLAUDE.md still has TDD directives as baseline, but the skill provides comprehensive enforcement when implementing.

### Stop Hook

**File:** `.claude/hooks/stop.sh`

**Purpose:** Post-response quality checks and reminders

**Checks:**
1. **Session tracking:** Is Chronicle tracking this work?
2. **Test coverage:** Was code written without tests?
3. **Chronicle search:** Did you search before implementing?

**Token cost:** ~100-150 tokens (status checks + message)

**Example output:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 QUALITY SELF-CHECK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️  Not in tracked Chronicle session
   💡 Tip: Run 'chronicle start claude' to track this work

🧪 Did you write tests first? (TDD red-green-refactor)

🔍 Did you search Chronicle first?
   💡 Try: mcp__chronicle__search_sessions(query="...")
   ⚡ 2,700x ROI - 1 second vs 20 minutes

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### PostToolUse Hook

**File:** `.claude/hooks/post-tool-use.sh`

**Purpose:** Track edited files for build checking (future enhancement)

**Triggers on:** Edit, Write, NotebookEdit tools

**Action:** Logs to `.claude/edit-log.txt` with timestamp

**Token cost:** 0 (runs silently)

**Future enhancement:** Stop hook will read edit log and run builds on affected repos

## Configuration

### Skill Rules

**File:** `.claude/config/skill-rules.json`

Defines trigger patterns for each enforcement:

```json
{
  "chronicleAdvocate": {
    "triggers": {
      "keywords": ["implement", "add", "create", "build", "fix", "debug"],
      "phrases": [
        "(?i)can't believe",
        "(?i)why (isn't|doesn't)",
        "(?i)this should"
      ],
      "excludes": ["read", "view", "show", "explain"]
    },
    "message": "🔍 SEARCH CHRONICLE FIRST\n\n..."
  }
}
```

### Settings

**File:** `.claude/settings.local.json`

Registers hooks with Claude Code:

```json
{
  "hooks": {
    "UserPromptSubmit": [{
      "hooks": [{
        "type": "command",
        "command": "~/.claude/hooks/user-prompt-submit.sh",
        "timeout": 5
      }]
    }],
    "Stop": [{
      "hooks": [{
        "type": "command",
        "command": "~/.claude/hooks/stop.sh",
        "timeout": 5
      }]
    }],
    "PostToolUse": [{
      "matcher": "Edit|Write|NotebookEdit",
      "hooks": [{
        "type": "command",
        "command": "~/.claude/hooks/post-tool-use.sh",
        "timeout": 5
      }]
    }]
  }
}
```

## Token Savings

### Before Hooks (Agents Only)

**Every message:**
- Chronicle Advocate: 400 tokens
- TDD Advocate: 300 tokens
- **Total: 700 tokens per message**

**50-message session:**
- Agent overhead: 35,000 tokens
- Cost: ~$0.35 per session

### After Hooks

**Average message:**
- Hooks (30% of messages): 50-150 tokens
- TDD Advocate: 300 tokens
- **Average: ~350 tokens per message**

**50-message session:**
- Agent + hook overhead: 17,500 tokens
- Cost: ~$0.18 per session

**Savings: 50% reduction = $0.17 per session**

## Agent Usage

### Chronicle Advocate - Manual Only

**When TO launch:**
- Planning complex multi-file features
- Need to review 5+ past sessions
- Deep roadmap/milestone analysis
- Session organization and documentation
- User explicitly asks for Chronicle guidance

**When NOT to launch (hooks handle it):**
- Simple "did you search?" reminders ✅ Hook
- Basic session tracking checks ✅ Hook
- One-off Chronicle searches ✅ Hook
- Quick roadmap lookups ✅ Hook

### TDD Advocate - Always Active

**Why keep as agent:**
- Test enforcement too critical for hooks alone
- Red-green-refactor cycle needs constant oversight
- Worth the 300 tokens per message
- Hooks supplement with lightweight reminders

## How Hooks Work

### Input Format

Hooks receive JSON via stdin:

```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/conversation.json",
  "cwd": "/Users/user/project",
  "permission_mode": "default",
  "hook_event_name": "UserPromptSubmit",
  "prompt": "I want to add a feature"  // UserPromptSubmit only
}
```

### Output Format

**Simple (stdout):**
```bash
echo "Reminder message"
exit 0  # Shows in transcript
```

**Structured (JSON):**
```bash
jq -n \
  --arg msg "Context to inject" \
  '{
    "decision": "approve",
    "reason": $msg,
    "systemMessage": $msg
  }'
```

### Exit Codes
- **0:** Success, stdout shown
- **2:** Blocking error, stderr fed to Claude
- **Other:** Non-blocking error, stderr to user

## Debugging

**Enable debug output:**
```bash
claude --debug
```

**Check hook execution:**
```bash
# Hooks run on every prompt/stop/edit
# Look for:
# - "Running hook: user-prompt-submit.sh"
# - "Hook output: ..."
# - "Hook completed in Xms"
```

**Common issues:**

1. **Hook doesn't run:**
   - Check executable: `chmod +x .claude/hooks/*.sh`
   - Check settings: `cat .claude/settings.local.json`
   - Restart Claude Code to reload config

2. **Hook times out:**
   - Default timeout: 5 seconds
   - Increase if needed: `"timeout": 10`
   - Check hook logic for slow operations

3. **JSON parsing errors:**
   - Test hook manually: `echo '{"prompt":"test"}' | .claude/hooks/user-prompt-submit.sh`
   - Validate JSON output with `jq`

## Future Enhancements

**Phase 2 (Planned):**
- Prettier auto-formatting on Stop
- Build checking on Stop (using edit log)
- File-based triggers (activate based on edited files)
- Error handling reminder (check for try-catch patterns)

**Phase 3 (Ideas):**
- Pre-commit hook (verify tests, build status)
- Session organization prompt (suggest title/tags)
- Lint checking on PostToolUse
- Automatic test generation reminders

## References

- **Inspiration:** [Reddit post on Claude Code best practices](https://www.reddit.com/r/ClaudeAI/comments/1oivjvm/claude_code_is_a_beast_tips_from_6_months_of/)
- **Claude Code Hooks:** https://docs.claude.com/en/docs/claude-code/hooks
- **Milestone #8:** Token-Efficient Hooks System
- **ROI Evidence:** Sessions 21, 30, 31 (45+ minutes wasted by not searching)

---

**Key Insight:** 90% of Chronicle Advocate's work can be handled by lightweight hooks at 10x lower token cost. Save the expensive agent for complex analysis where it adds real value.
