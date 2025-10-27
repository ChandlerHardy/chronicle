# Chronicle - AI Assistant Guide

> **📌 Load the Chronicle Advocate Agent First!**
>
> The Chronicle Advocate agent enforces best practices:
> - ⚡ Pre-flight checklist (search first, use MCP, check roadmap)
> - 🎯 Core directives with examples
> - 📚 Complete MCP tools reference
> - 🔄 Typical workflows
>
> **Setup:** See [AGENTS.md](./AGENTS.md) for agent prompts and cross-platform setup.
>
> **This file:** Project-specific technical context for developing Chronicle itself.

---

## 🔧 Working on Chronicle (The Meta Project)

**Chronicle is meta:** It tracks its own development.

**Key differences when working on Chronicle vs using Chronicle:**
1. **Dogfooding:** Every session you run is tracked, every mistake is in the database
2. **Search first:** Past sessions contain solutions to problems you might encounter
3. **MCP server restart required:** After changing `backend/mcp/server.py`, restart Claude Code
4. **Test with Chronicle:** Use `chronicle start claude` to track your development work

---

## 🏗️ Architecture

### Data Flow

```
chronicle start claude
    ↓
Unix `script` captures terminal I/O
    ↓
On exit: Transcript → ~/.ai-session/sessions/session_N.log
    ↓
Database entry created (transcript stored inline)
    ↓
AI summary generated on first view (chunked for large sessions)
```

### Key Locations

- **Database**: `~/.ai-session/sessions.db` (SQLite)
- **Transcripts**: Stored inline in database `session_transcript` column
- **Config**: `~/.ai-session/config.yaml`
- **MCP Config**: `~/.mcp.json` (global) or `.mcp.json` (project-local)

### Database Tables

**ai_interactions** (main session table):
- `is_session=True` → Full session with transcript
- `is_session=False` → One-shot interaction
- `session_transcript` → Full transcript text (stored inline)
- `summary_generated` → Whether AI summary exists
- `title`, `tags`, `keywords` → Organization fields
- `parent_session_id`, `related_session_ids` → Session linking

**commits**:
- Git commit tracking (SHA, message, files_changed, branch, author, repo_path)

**project_milestones**:
- Feature/project tracking (title, description, status, type, priority, tags)
- `related_sessions`, `related_commits` → JSON arrays

**next_steps**:
- TODO items (description, priority, effort, category, completed)
- `related_milestone_id` → Links to milestone

**session_summary_chunks**:
- Stores intermediate summaries for chunked summarization
- Enables resume capability if summarization fails

---

## 📝 Session Recording

### How It Works

```bash
# User runs
chronicle start claude

# Spawns
script -q ~/.ai-session/sessions/session_N.log claude

# Captures all terminal I/O until user types `exit`
```

### Important Note

**Current session is NOT tracked** unless started with `chronicle start claude`.

If user asks about tracking the current session, remind them it's not being tracked and suggest they exit and restart with `chronicle start claude`.

---

## 🧪 Summarization

### Automatic (Lazy Loading)

```bash
chronicle session 16
# First view: Triggers chunked summarization
# Subsequent views: Returns cached summary
```

### Chunking for Large Sessions

- Default: 10,000 lines per chunk
- Cumulative summarization (each chunk updates previous summary)
- Automatic retry: 3 attempts per chunk with exponential backoff
- Resume capability: If fails mid-process, can resume from last successful chunk

### Retry Logic

- Rate limit errors: 15s, 30s, 45s delays
- Other errors: 5s, 10s, 20s (exponential backoff)
- After 3 failures: Saves partial summary, can resume later

---

## ⚙️ Configuration

### Required for Summarization

```bash
chronicle config ai.gemini_api_key YOUR_KEY
# Or: export GEMINI_API_KEY=...
```

### Key Settings

- `ai.default_model` → Gemini model (default: `gemini-2.0-flash`)
- `ai.gemini_api_key` → API key for summarization
- `ai.summarization_provider` → "gemini" or "ollama"

---

## 🚨 Known Issues

### Database Size (110MB for 13 sessions)
**Cause**: Transcripts stored inline (~47MB of text)
**Status**: Optimization planned (move to external files)
**Impact**: None for functionality

### MCP Server Hangs
**Cause**: Configuration changes require restart
**Fix**: Restart Claude Code after editing `~/.mcp.json`

### Windows Support
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
3. Test with fresh database: `rm ~/.ai-session/sessions.db && chronicle init`
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

2. Test with direct MCP call (restart Claude Code to reload server)
3. Document in `MCP_SERVER.md`

---

## 📚 File Reference

**Critical Files:**
- `backend/main.py` - CLI entry point
- `backend/database/models.py` - Database schema (SQLAlchemy models)
- `backend/services/summarizer.py` - Gemini integration, chunking logic
- `backend/cli/commands.py` - All CLI commands
- `backend/cli/formatters.py` - Rich terminal formatting
- `backend/mcp/server.py` - MCP server (21 tools)
- `scripts/chronicle-mcp` - MCP server executable

**Configuration:**
- `.mcp.json.example` - Example MCP configuration
- `pyproject.toml` - Project metadata, dependencies

**Documentation:**
- `AGENTS.md` - Chronicle Advocate & TDD Advocate (cross-platform)
- `MCP_SERVER.md` - MCP server guide (21 tools documented)
- `README.md` - User-facing documentation
- `DEVELOPMENT_HISTORY.md` - Project history
- `chronicle-skills/` - Claude Skills definitions

---

## 🔗 Quick Links

- Database: `~/.ai-session/sessions.db`
- Sessions: `~/.ai-session/sessions/`
- Config: `~/.ai-session/config.yaml`
- MCP config: `~/.mcp.json`

---

**For universal Chronicle directives and workflows, see the Chronicle Advocate agent in [AGENTS.md](./AGENTS.md).**
