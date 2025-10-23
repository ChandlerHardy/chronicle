# Chronicle - AI Assistant Guide

> **Purpose**: This document tells AI assistants how to use Chronicle effectively.
> **For project history**: See [DEVELOPMENT_HISTORY.md](./DEVELOPMENT_HISTORY.md)
> **For users**: See [README.md](./README.md)

---

## 🎯 Core Directive: Use MCP Tools First

**When querying Chronicle data, ALWAYS use MCP server tools, not CLI commands.**

**Why:**
- MCP returns structured JSON (easy to parse)
- CLI returns formatted text (designed for humans)
- MCP is faster (no shell overhead)
- Better filtering and query capabilities

**Available MCP Tools:**
```python
mcp__chronicle__get_sessions(limit=10, tool="claude-code", repo_path="/path", days=7)
mcp__chronicle__get_session_summary(session_id=16)
mcp__chronicle__search_sessions(query="MCP server", limit=10)
mcp__chronicle__get_commits(limit=20, repo_path="/path", days=7)
mcp__chronicle__search_commits(query="retry logic", limit=20)
mcp__chronicle__get_timeline(days=1, repo_path="/path")
mcp__chronicle__get_stats(days=7)
```

**Example:**
```python
# ❌ DON'T:
Bash("chronicle sessions --repo chronicle")  # Returns formatted text

# ✅ DO:
mcp__chronicle__get_sessions(repo_path="/Users/.../chronicle")  # Returns JSON
```

**CLI commands are for:**
- User-facing operations (`chronicle start`, `chronicle config`)
- File system operations not exposed by MCP
- When user explicitly requests CLI output

---

## 🤖 Chronicle Skills

Three skills are published to Claude marketplace:

1. **chronicle-workflow** - Complete workflow guidance
2. **chronicle-session-documenter** - Export sessions to Obsidian
3. **chronicle-context-retriever** - Search past work

**Skills use MCP tools internally** - they add workflow intelligence on top of raw MCP data.

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
