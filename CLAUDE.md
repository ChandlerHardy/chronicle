# Chronicle - AI Assistant Guide

> **Purpose**: Project-specific guidance for working on Chronicle itself
> **For Chronicle usage directives**: See `chronicle-assistant-guide` skill (universal, works in all projects)
> **For project history**: See [DEVELOPMENT_HISTORY.md](./DEVELOPMENT_HISTORY.md)
> **For users**: See [README.md](./README.md)

---

## 📌 IMPORTANT: Load the Chronicle Assistant Guide Skill

**Before working on Chronicle, load the universal skill:**
```
/skill add chronicle-skills/chronicle-assistant-guide
```

This skill contains:
- ⚡ Pre-flight checklist (search first, use MCP, check roadmap)
- 🎯 Core directives with real examples
- 📚 MCP tools reference
- 🔄 Typical workflows

**Why separate?** The `chronicle-assistant-guide` skill works across ALL projects with Chronicle MCP. This CLAUDE.md file contains Chronicle-the-project-specific context.

---

## 🔧 Project-Specific Context

### Working on Chronicle Itself

**Chronicle is meta:** It tracks its own development. This means:
- Every session is recorded
- Every mistake is in the database
- Search first to avoid repeating work!

**Key differences when working on Chronicle vs using Chronicle:**
1. **Test with Chronicle:** Use `chronicle start claude` to track your work
2. **Dogfooding:** The tool must work well for its own development
3. **MCP server needs restart:** After changing `backend/mcp/server.py`, restart Claude Code

---

## 🎯 Quick Reference for Chronicle Development

### ALWAYS Use MCP Tools (Never CLI)

**When working with Chronicle data, ALWAYS use MCP tools or Skills, NEVER use CLI commands.**

**Priority Order:**
1. ✅ **Chronicle Skills** (chronicle-workflow, chronicle-session-documenter, chronicle-context-retriever, chronicle-project-tracker)
2. ✅ **MCP tools** (mcp__chronicle__* functions - fast, programmatic access)
3. ❌ **CLI commands** (ONLY for user-facing operations like `chronicle start` - slow, not programmatic)

**Why MCP over CLI:**
- **Speed**: MCP queries database directly (<10ms), CLI spawns subprocess (>100ms)
- **Programmatic**: Returns structured JSON, not formatted text
- **Reliable**: No parsing of human-readable output
- **Efficient**: No terminal formatting overhead

**Examples:**
```python
# ✅ CORRECT (MCP):
roadmap = mcp__chronicle__get_roadmap(days=7)
sessions = mcp__chronicle__search_sessions(query="storage", limit=5)

# ❌ WRONG (CLI - slow, hard to parse):
Bash("chronicle roadmap")
Bash("chronicle search 'storage'")
```

---

## 🤖 Chronicle Skills (USE THESE!)

Four skills are available and should be your **first choice** for Chronicle interactions:

### 1. chronicle-workflow
**Use for:** Starting sessions, workflow guidance, best practices
- Checks if current session is tracked
- Guides user through Chronicle workflow
- Explains session start/end process
- Multi-project tracking advice

**Trigger phrases:**
- "starting a new session"
- "how do I track this work?"
- "chronicle workflow"
- "set up Chronicle"

### 2. chronicle-session-documenter
**Use for:** Documenting completed sessions to Obsidian
- Queries Chronicle database for session details
- Retrieves AI summaries
- Creates structured Obsidian notes
- Adds metadata, tags, wikilinks

**Trigger phrases:**
- "document session X to Obsidian"
- "create a note for this session"
- "export session to vault"
- "log this work"

### 3. chronicle-context-retriever
**Use for:** Searching past work and retrieving context
- Searches Obsidian vault for session notes
- Finds past approaches and decisions
- Extracts relevant context
- Helps avoid repeating work

**Trigger phrases:**
- "what did I do yesterday?"
- "how did I implement X?"
- "find sessions about Y"
- "show me past work on Z"

### 4. chronicle-project-tracker
**Use for:** Managing project development with milestones and roadmap
- Plan features with milestones
- Break down work into next steps
- Link sessions to milestones
- View project roadmap and progress
- Generate development reports
- Eliminate manual documentation updates

**Trigger phrases:**
- "what should I work on next?"
- "show me the roadmap"
- "what's in progress?"
- "plan a new feature"
- "link this session to a milestone"
- "what did we accomplish this week?"

**Example:**
```python
# ✅ DO (Skills first!):
User: "Document session 16 to my Obsidian vault"
→ Load chronicle-session-documenter skill
→ Skill handles querying DB, formatting note, writing to vault

# ⚠️ ONLY IF NO SKILL EXISTS:
mcp__chronicle__get_session_summary(session_id=16)

# ❌ DON'T:
Bash("chronicle session 16")  # Use skills or MCP, not CLI
```

---

## 🔧 When to Use MCP Tools Directly

**Only use raw MCP tools when:**
- No appropriate skill exists for the task
- Need low-level database access for debugging
- Building new functionality that Skills don't cover

**Available MCP Tools** (use sparingly during testing):

**Session & Commit Tracking:**
```python
# List sessions (summaries excluded by default for performance)
mcp__chronicle__get_sessions(limit=10, tool="claude-code", repo_path="/path", days=7)
mcp__chronicle__get_sessions(limit=10, include_summaries=True)  # Optional: include summaries

# Get single session details with full summary
mcp__chronicle__get_session_summary(session_id=16)

# Batch retrieve summaries for multiple sessions (NEW!)
mcp__chronicle__get_sessions_summaries(session_ids=[15, 16, 17])

# Search and other queries
mcp__chronicle__search_sessions(query="MCP server", limit=10)
mcp__chronicle__get_commits(limit=20, repo_path="/path", days=7)
mcp__chronicle__search_commits(query="retry logic", limit=20)
mcp__chronicle__get_timeline(days=1, repo_path="/path")
mcp__chronicle__get_stats(days=7)
```

**Project Tracking (New!):**
```python
mcp__chronicle__get_milestones(status="in_progress", milestone_type="feature", limit=20)
mcp__chronicle__get_milestone(milestone_id=1)
mcp__chronicle__get_next_steps(completed=False, milestone_id=1, limit=20)
mcp__chronicle__get_roadmap(days=7)
mcp__chronicle__update_milestone_status(milestone_id=1, new_status="completed")
mcp__chronicle__complete_next_step(step_id=1)
```

**CLI commands are for:**
- User-facing operations (`chronicle start`, `chronicle config`)
- When user explicitly requests CLI output

---

## 🏗️ Architecture Essentials

### Data Flow

```
1. User runs: chronicle start claude
   ↓
2. Unix `script` captures full terminal I/O
   ↓
3. On exit: Transcript saved to ~/.ai-session/sessions/session_N.log
   ↓
4. Database entry created (with transcript stored inline - currently)
   ↓
5. AI summary generated on first view (chunked for large sessions)
```

### Key Locations

- **Database**: `~/.ai-session/sessions.db` (SQLite)
- **Transcripts**: Stored in database `session_transcript` column (TEXT)
- **Config**: `~/.ai-session/config.yaml`
- **MCP Config**: `~/.mcp.json` (global) or `.mcp.json` (project-local)

### Database Tables

**ai_interactions** - Main session/interaction table:
- `is_session=True` → Full session with transcript
- `is_session=False` → One-shot interaction
- `session_transcript` → Full transcript text (currently inline, ~110MB for 13 sessions)
- `summary_generated` → Whether AI summary exists

**session_summary_chunks** - For large sessions:
- Stores intermediate summaries for sessions split into chunks
- Enables resume capability if summarization fails mid-process

---

## 📝 How Chronicle Sessions Work

### Starting a Session (User runs this):
```bash
chronicle start claude
# Spawns: script -q ~/.ai-session/sessions/session_N.log claude
# Captures all terminal I/O
```

### Ending a Session:
- User types `exit` or Ctrl-D
- Metadata saved to database
- Transcript stored inline in database
- Summary generated lazily (on first view)

###Retroactive Capture (if user forgets):
```bash
chronicle add-manual -d "What I accomplished"
```
- Creates database entry without transcript
- Can be summarized later based on description

### Important: Current Session is NOT Tracked

If user is already in a Claude Code session and asks about Chronicle:
- This session is **NOT being tracked** (unless started with `chronicle start claude`)
- Suggest they exit and restart with `chronicle start claude` for tracking

---

## 🔍 Common Queries

### "What did I do yesterday?"
```python
sessions = mcp__chronicle__get_timeline(days=1)
# Parse JSON, summarize activities
```

### "Find sessions about authentication"
```python
sessions = mcp__chronicle__search_sessions(query="authentication", limit=5)
# Returns sessions with "authentication" in summaries or prompts
```

### "How long did I work on the chronicle repo?"
```python
sessions = mcp__chronicle__get_sessions(repo_path="/Users/.../chronicle")
# Sum duration_minutes from all sessions
```

---

## ⚙️ Configuration

### Gemini API Key (required for summarization):
```bash
chronicle config ai.gemini_api_key YOUR_KEY
# Or: export GEMINI_API_KEY=...
```

### Important Settings:
- `ai.default_model` → Gemini model (default: `gemini-2.0-flash`)
- `ai.gemini_api_key` → API key for summarization

---

## 🧪 Summarization

### Automatic (on first view):
```bash
chronicle session 16
# If not summarized: triggers chunked summarization automatically
# Chunks: 10,000 lines each, with automatic retry (3 attempts per chunk)
```

### Manual:
```bash
chronicle summarize-chunked 16 --chunk-size 5000
```

### How It Works:
1. Split transcript into chunks (default: 10K lines)
2. Summarize first chunk
3. For each subsequent chunk: update cumulative summary
4. Save chunks to `session_summary_chunks` table
5. If fails: resume from last successful chunk
6. Automatic retry: 3 attempts per chunk with exponential backoff

### Retry Logic (Oct 22, 2025):
- Rate limit errors: wait 15s, 30s, 45s
- Other errors: wait 5s, 10s, 20s (exponential backoff)
- After 3 failures: saves partial summary, can resume later

---

## 📊 Repository Organization

Chronicle auto-detects repositories:
- Walks up from `working_directory` to find git root
- Stores `repo_path` in database
- Filter sessions by repo: `get_sessions(repo_path="/path")`

**Multi-repo workflow:**
```python
# Chronicle repo sessions
chronicle_sessions = mcp__chronicle__get_sessions(repo_path="/Users/.../chronicle")

# My app sessions
app_sessions = mcp__chronicle__get_sessions(repo_path="/Users/.../my-app")
```

---

## 🚨 Known Issues & Workarounds

### Issue: Database Size (110MB for 13 sessions)
**Cause**: Transcripts stored inline in database (47MB of text)
**Status**: Optimization planned (move to external files)
**Impact**: None for functionality, just larger database file

### Issue: MCP Server Hangs
**Cause**: Usually due to MCP configuration changes requiring restart
**Fix**: User must restart Claude Code after editing `~/.mcp.json`

### Issue: Windows Support
**Status**: Not supported (requires Unix `script` command)
**Workaround**: Could use PowerShell transcript in future

---

## 🛠️ Development Tasks

### Adding a New CLI Command

1. Add to `backend/cli/commands.py`:
```python
@cli.command()
@click.option('--flag', help='Description')
def my_command(flag: str):
    """Command description."""
    # Implementation
```

2. Use formatters from `backend/cli/formatters.py`
3. Add tests to `tests/test_*.py`

### Modifying Database Schema

1. Update `backend/database/models.py`
2. Add migration in `backend/database/migrate.py`
3. Test with fresh database
4. Update this document's schema section

### Adding MCP Tools

1. Add to `backend/mcp/server.py`:
```python
@mcp.tool()
def my_tool(param: str) -> str:
    """Tool description."""
    # Implementation
    return json.dumps(result)
```

2. Test with direct MCP call
3. Document in MCP_SERVER.md

---

## 📚 File Reference

**Critical files:**
- `backend/main.py` - CLI entry point
- `backend/database/models.py` - Database schema
- `backend/services/summarizer.py` - Gemini integration, chunking logic
- `backend/cli/commands.py` - All CLI commands
- `backend/mcp/server.py` - MCP server implementation
- `scripts/chronicle-mcp` - MCP server executable

**Configuration:**
- `.mcp.json.example` - Example MCP configuration
- `pyproject.toml` - Project metadata, dependencies

**Documentation:**
- `CLAUDE.md` - This file (AI assistant guide)
- `DEVELOPMENT_HISTORY.md` - Project history and completed features
- `README.md` - User documentation
- `MCP_SERVER.md` - MCP server documentation
- `chronicle-skills/` - Claude Skills definitions

---

## 🔗 Quick Links

- Database: `~/.ai-session/sessions.db`
- Sessions directory: `~/.ai-session/sessions/`
- Config: `~/.ai-session/config.yaml`
- MCP config: `~/.mcp.json`

---

## 💡 Best Practices

1. **Always use MCP tools** for querying Chronicle data
2. **Check if session is being tracked** before assuming it is
3. **Suggest `chronicle start`** when user talks about tracking
4. **Use chunked summarization** for sessions >50K lines
5. **Commit with Chronicle's git format** (includes co-author line)

---

**This document focuses on HOW to use Chronicle. For project history, see DEVELOPMENT_HISTORY.md.**
