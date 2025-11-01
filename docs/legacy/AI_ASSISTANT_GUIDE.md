# Chronicle - Quick Reference for AI Assistants

> A quick reference for AI coding assistants (Claude Code, Cursor, Gemini CLI, etc.) on how to help users leverage Chronicle for development memory.

**Last Updated:** October 27, 2025 (Phase 4 - MCP & Project Management)

---

## Quick Start Workflow

**If user asks about Chronicle or session tracking:**

```bash
# Suggest this workflow to the user:
1. Exit current session
2. Run: chronicle start claude
3. Continue working (session is now being tracked)
4. When done: exit
5. View summary: chronicle session <id>
```

---

## Key Concepts

**Chronicle sessions are started MANUALLY:**
- User runs `chronicle start claude` BEFORE launching Claude Code
- This wraps the session and captures the full transcript
- Sessions are NOT automatically tracked - user must explicitly start tracking
- **You CANNOT start Chronicle from within an active session** (creates nested sessions)

**Auto-detection:**
- Sessions auto-detect the git repository based on working directory
- All commits made during the session are automatically linked
- Summaries are generated on-demand with AI (lazy loading)

---

## Access Methods

### Method 1: MCP Tools (Recommended - Fast & Structured)

**If Chronicle MCP server is available**, use these tools for direct programmatic access:

```python
# Search sessions (10x faster than CLI)
mcp__chronicle__search_sessions(query="authentication", limit=10)

# Get recent sessions with structured JSON
mcp__chronicle__get_sessions(limit=10, days=7, include_summaries=True)

# View specific session
mcp__chronicle__get_session_summary(session_id=5)

# Check roadmap and planning
mcp__chronicle__get_roadmap(days=7)
mcp__chronicle__get_next_steps(completed=False, limit=20)
mcp__chronicle__get_milestones(status="in_progress")

# Project management
mcp__chronicle__complete_next_step(step_id=3)
mcp__chronicle__update_milestone_status(milestone_id=2, new_status="completed")

# Timeline and commits
mcp__chronicle__get_timeline(days=1, repo_path="/path/to/repo")
mcp__chronicle__get_commits(limit=20, days=7, author="username")
```

**Benefits:**
- Returns structured JSON (easy to parse)
- 10x faster than CLI commands
- No shell overhead
- Direct database access

See [MCP_SERVER.md](MCP_SERVER.md) for complete tool reference (21 tools).

### Method 2: Bash Commands (Fallback - Works Everywhere)

**If MCP server is NOT available** (minimal installation):

```bash
# Search and view sessions
chronicle search "query"
chronicle sessions
chronicle session <id>

# Daily/weekly views
chronicle show today
chronicle timeline today
chronicle summarize today

# Project management
chronicle roadmap
chronicle next-steps
chronicle milestones

# Multi-project filtering
chronicle sessions --repo /path/repo
chronicle show today --repo /path/repo
```

**When to use:**
- User installed without MCP: `pip install -e .`
- Restricted environments (FreeBSD, corporate systems)
- Displaying output to user (Rich terminal formatting)

---

## Best Practices for AI Assistants

### 1. Search Before Implementing (CRITICAL)

**Before any implementation:**
```python
# With MCP:
results = mcp__chronicle__search_sessions(query="retry logic", limit=5)

# Without MCP:
Bash("chronicle search 'retry logic'")
```

**Why?** Searching takes 1 second. Reinventing takes 10-20 minutes. (2,700x ROI)

### 2. Check Roadmap Before Planning

```python
# With MCP:
roadmap = mcp__chronicle__get_roadmap(days=7)

# Without MCP:
Bash("chronicle roadmap")
```

Prevents duplicate work on already-planned features.

### 3. Remind Users to Track Sessions

If meaningful work is happening and user hasn't started tracking:
```
"This looks like significant work. Would you like to track this session?
Exit and run `chronicle start claude` to capture everything."
```

### 4. Suggest Session Organization

After completing work:
```
"Great work! When you view this session later with `chronicle session <id>`,
consider adding:
- Title: 'Implement retry logic for API calls'
- Tags: retry, error-handling, api, robustness"
```

### 5. Prefer MCP Over CLI for Programmatic Access

**Good:**
```python
sessions = mcp__chronicle__get_sessions(limit=10)
for session in json.loads(sessions):
    # Process structured data
```

**Avoid:**
```python
output = Bash("chronicle sessions")
# Now you have to parse terminal output
```

---

## When Working IN the Chronicle Project

1. **Current session is likely NOT tracked** unless user explicitly started it
2. **DO** use Chronicle to search past solutions
3. **DO** search before implementing (dogfooding!)
4. **DO** check the roadmap before planning new features
5. **DO NOT** run `chronicle start` from within an active session (nested sessions fail)

See [CLAUDE.md](CLAUDE.md) for Chronicle-specific development context.

---

## When Working on OTHER Projects

### Proactive Suggestions

**Before starting work:**
- "Would you like to track this session? Run `chronicle start claude` before we begin."
- Search Chronicle if user asks "Have we done this before?"

**During work:**
- "Chronicle will automatically track all commits we make during this session."
- Use Chronicle to check if similar work was done previously

**After work:**
- "You can view what we accomplished with `chronicle session <id>`"
- "Or see today's work across all projects: `chronicle show today`"

---

## Command Reference

### Session Management

```bash
chronicle start claude                # Track Claude Code session
chronicle start gemini                # Track Gemini CLI session
chronicle start qwen                  # Track Qwen CLI session
chronicle sessions                    # List recent sessions
chronicle session <id>                # View session with AI summary
```

### Search & Discovery

```bash
chronicle search "query"              # Search all sessions
chronicle timeline today              # Combined commits + sessions
chronicle show today                  # Git commits only
chronicle summarize today             # AI summary of today's work
```

### Project Management

```bash
chronicle roadmap                     # View project roadmap
chronicle milestones                  # List milestones
chronicle next-steps                  # View TODO items
chronicle stats                       # Usage statistics
```

---

## Specialized Agents

Chronicle includes two specialized agents for enhanced workflows:

### Chronicle Advocate Agent
**Purpose:** Enforces search-first workflow, prevents wasted effort

**Triggers:**
- Before implementing new features
- When planning new work
- When user hasn't started tracking
- After completing significant work

**Benefits:** Enforces 2,700x ROI search-first discipline

### TDD Advocate Agent
**Purpose:** Ensures tests are written before implementation

**Triggers:**
- Before implementing new features
- After code is written without tests
- Before committing changes
- During refactoring

See [AGENTS.md](AGENTS.md) for complete agent documentation.

---

## Integration into Your Project

To enable Chronicle awareness in your development projects:

1. **Copy integration template** from [docs/INTEGRATION.md](docs/INTEGRATION.md)
2. **Add to your project's CLAUDE.md** (or equivalent AI guide)
3. **Configure MCP** (optional, for fast programmatic access)

This gives AI assistants proactive Chronicle awareness without manual prompting.

---

## How Chronicle Works

### 1. Session Recording

```
chronicle start claude
    ↓
Unix `script` captures terminal I/O
    ↓
Full transcript saved inline in database
    ↓
Metadata tracked (duration, tool, repo, etc.)
```

### 2. Summarization (Lazy Loading)

```
User runs: chronicle session 5
    ↓
First view triggers AI summarization
    ↓
Chunked processing for large sessions (10k lines/chunk)
    ↓
Summary cached forever
    ↓
Keywords extracted for searchability
```

### 3. Commit Linking

```
Commits made during session
    ↓
Auto-linked within ±30min window
    ↓
Repository auto-detected from working directory
    ↓
Queryable via timeline and session views
```

---

## Storage Locations

- **Database:** `~/.ai-session/sessions.db` (SQLite)
- **Transcripts:** Stored inline in database `session_transcript` column
- **Configuration:** `~/.ai-session/config.yaml`
- **MCP Config:** `~/.mcp.json` (global) or `.mcp.json` (project-local)

---

## Troubleshooting

**"Session not being tracked":**
- Must run `chronicle start claude` BEFORE launching Claude Code, not during
- Cannot start tracking mid-session

**"Nested session error":**
- Cannot run `chronicle start` from within an already-tracked session
- User must exit and restart

**"MCP tools not available":**
- Check if installed with MCP: `pip install -e ".[mcp]"`
- Verify `~/.mcp.json` configuration
- Restart Claude Code after MCP config changes

**"Summary generation failed":**
- Check Gemini API key: `chronicle config ai.gemini_api_key`
- Or set environment variable: `GEMINI_API_KEY=...`
- Large sessions use chunked summarization (automatic retry)

---

## Example User Conversations

**User:** "How do I track this session?"
**AI:** "Chronicle needs to be started before the session begins. Let's exit and restart with `chronicle start claude` to track everything."

**User:** "Can you summarize what we did today?"
**AI:** "Yes! Let me check Chronicle..."
```python
mcp__chronicle__get_timeline(days=1)
```
"Here's what we accomplished today: [summary from Chronicle]"

**User:** "Have we implemented retry logic before?"
**AI:** "Let me search Chronicle..."
```python
mcp__chronicle__search_sessions(query="retry logic", limit=5)
```
"Yes! Found Session #31 where we implemented retry logic for the API. Let me show you that approach..."

**User:** "I have multiple projects, how do I filter?"
**AI:** "You can filter by repository:"
```bash
chronicle sessions --repo /path/to/your/project
chronicle timeline today --repo /path/to/your/project
```

---

## Further Reading

- **[docs/INTEGRATION.md](docs/INTEGRATION.md)** - Template for integrating Chronicle into your projects
- **[README.md](README.md)** - Full project documentation
- **[MCP_SERVER.md](MCP_SERVER.md)** - Complete MCP tools reference (21 tools)
- **[AGENTS.md](AGENTS.md)** - Chronicle Advocate & TDD Advocate documentation
- **[CLAUDE.md](CLAUDE.md)** - Context for developing Chronicle itself
- **`chronicle --help`** - CLI command reference

---

**Questions?** Open an issue at https://github.com/ChandlerHardy/chronicle/issues
