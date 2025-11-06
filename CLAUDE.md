# Chronicle - Project-Specific Development Guide

> **📌 Project Status: SUNSET (November 2025)**
>
> **📌 Recommendation**: Use episodic-memory skill from superpowers repository for new implementations
>
> **📌 Universal Directives**: See `~/.claude/CLAUDE.md` for mandatory workflows
>
> **📌 Load the Chronicle Advocate Agent** for project-specific enforcement:
> - See [AGENTS.md](./AGENTS.md) for agent prompts and setup
>
> **This file**: Chronicle-specific architecture, implementation details, and workflows (preserved for historical reference)

---

## 🔧 Working on Chronicle (The Meta Project)

**Chronicle is meta:** It tracks its own development.

**Key differences when working on Chronicle vs using Chronicle:**
1. **Dogfooding:** Every session you run is tracked, every mistake is in the database
2. **Search first:** Past sessions contain solutions to problems you might encounter
3. **MCP server restart required:** After changing `backend/mcp/server.py`, restart Claude Code
4. **Test with Chronicle:** Use `chronicle start claude` to track your development work

---

## 🎯 Chronicle Skills (Use These First!)

**BEFORE manually calling MCP tools, check if a skill exists for the task:**

| Task | Use This Skill | Instead of Manual |
|------|----------------|-------------------|
| 📝 Export session to Obsidian | `chronicle-session-documenter` | Manual `mcp__chronicle__get_session_summary()` + `mcp__obsidian__write_note()` calls |
| 🔍 Search past sessions for context | `chronicle-context-retriever` | Manual search and analysis across multiple sessions |
| 🔄 Complete Chronicle workflow guidance | `chronicle-workflow` | Ad-hoc workflow instructions |
| 📊 Manage milestones and roadmap | `chronicle-project-tracker` | Manual milestone/next step operations |

### Skill Locations

- **User skills:** `~/.claude/plugins/marketplaces/chronicle-skills/chronicle-skills/`
- **Project skills:** `chronicle-skills/` (for plugin marketplace)

**Available skills documented in:** `chronicle-skills/README.md`

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
Cleaned → ~/.ai-session/sessions/session_N.cleaned (v6+ optimization)
    ↓
Database entry created (transcript reference, NOT inline storage)
    ↓
AI summary generated on first view (chunked for large sessions)
```

### Key Locations

- **Database**: `~/.ai-session/sessions.db` (SQLite)
- **Transcripts**: Stored in external files (v6+ optimization, see Milestone #2)
  - `.log` files: Raw terminal output
  - `.cleaned` files: Processed transcripts with control chars removed
  - Database `session_transcript` column: NULL for v6+ sessions (uses file storage)
- **Config**: `~/.ai-session/config.yaml`
- **MCP Config**: `~/.mcp.json` (global) or `.mcp.json` (project-local)

### Database Tables

**ai_interactions** (main session table):
- `is_session=True` → Full session with transcript
- `is_session=False` → One-shot interaction
- `session_transcript` → **NULL for v6+ sessions** (stored in `.cleaned` files instead)
  - **Legacy sessions**: Inline text storage (pre-v6)
  - **Modern sessions**: NULL (see Milestone #2 - transcript optimization)
  - **Fallback chain**: database → `.cleaned` file → `.log` file → None
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

### Gemini Model Fallback Strategy

Chronicle automatically selects the best available Gemini model based on **session size** and **quota usage**:

- **Small/Medium Sessions (<50K)**: Prefers gemini-2.5-flash (latest features)
- **Large Sessions (>50K)**: Prefers gemini-2.0-flash (1M TPM for 10K chunks)
- **Automatic chunk adjustment**: 10K lines for 1M TPM models, 5K lines for 250K TPM models
- **Smart failover**: Tracks quota usage and falls back automatically

**See [docs/GEMINI_MODELS.md](docs/GEMINI_MODELS.md) for complete model selection logic and configuration.**

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
  - **Available models**: `gemini-2.0-flash`, `gemini-2.0-flash-lite`, `gemini-2.5-flash`, `gemini-2.5-flash-preview-09-2025`, `gemini-2.5-flash-lite`
  - **Note**: Chronicle auto-selects models based on quota, so you rarely need to change this
- `ai.gemini_api_key` → API key for summarization
- `ai.summarization_provider` → "gemini" or "ollama"

---

## 🚨 Known Issues

### Database Size ✅ RESOLVED
**Previous issue**: 110MB for 13 sessions (transcripts stored inline)
**Resolution**: Milestone #2 - Moved transcripts to external `.cleaned` files
**Current**: Database only stores metadata, transcripts in separate files
**Impact**: Database is now much smaller and faster

### MCP Server Hangs
**Cause**: Configuration changes require restart
**Fix**: Restart Claude Code after editing `~/.mcp.json`

### Windows Support
**Status**: Not supported (requires Unix `script` command)
**Workaround**: Could use PowerShell transcript in future

---

## 🛠️ Development Tasks

### 🚨 Chronicle Development Checklist

**Before starting Chronicle-specific work:**

1. **Universal directives already covered in** `~/.claude/CLAUDE.md`
2. **MCP server restart required** after changing `backend/mcp/server.py`
3. **Dogfooding enabled** - your work is tracked by Chronicle itself

---

### Adding a New CLI Command

**✅ TDD APPROACH (REQUIRED):**

1. **Write tests FIRST** in `tests/test_*.py`:
```python
def test_my_command_success(temp_db):
    """Test my_command with valid input."""
    result = runner.invoke(cli, ['my-command', '--flag', 'value'])
    assert result.exit_code == 0
    assert "expected output" in result.output

def test_my_command_invalid_input(temp_db):
    """Test my_command with invalid input."""
    result = runner.invoke(cli, ['my-command', '--flag', 'bad'])
    assert result.exit_code != 0
    assert "error message" in result.output
```

2. **Run tests** (they should FAIL):
```bash
pytest tests/test_*.py -v  # Red phase
```

3. **Implement command** in `backend/cli/commands.py`:
```python
@cli.command()
@click.option('--flag', help='Description')
def my_command(flag: str):
    """Command description."""
    # Implementation
```

4. **Use formatters** from `backend/cli/formatters.py`

5. **Run tests again** (they should PASS):
```bash
pytest tests/test_*.py -v  # Green phase
```

**❌ DO NOT skip tests. User will call you out.**

### Modifying Database Schema

**✅ TDD APPROACH (REQUIRED):**

1. **Write tests FIRST** that verify schema changes
2. **Update** `backend/database/models.py`
3. **Add migration** in `backend/database/migrate.py`
4. **Test with fresh database**: `rm ~/.ai-session/sessions.db && chronicle init`
5. **Run all tests**: `pytest tests/ -v`
6. **Update this document's schema section**

**Search Chronicle first!** Schema changes often already implemented.

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
- `docs/HOOKS.md` - Token-efficient hooks system (replaces Chronicle Advocate)
- `docs/GEMINI_MODELS.md` - Model selection and fallback strategy
- `REMOTE_SUMMARIZE_WORKFLOW.md` - Remote summarization guide (FreeBSD ↔ Mac)
- `PROVIDER_SWITCHING.md` - Switch between Anthropic and Z.AI providers

---

## 🔗 Quick Links

- Database: `~/.ai-session/sessions.db`
- Sessions: `~/.ai-session/sessions/`
- Config: `~/.ai-session/config.yaml`
- MCP config: `~/.mcp.json`

---

## 🎯 Chronicle-Specific Reminders

**When working on Chronicle:**

1. **MCP server restart required** after changing `backend/mcp/server.py`
2. **Dogfooding enabled** - your development is tracked by Chronicle itself
3. **Universal directives apply** - see `~/.claude/CLAUDE.md` for mandatory workflows

**For universal Chronicle directives and workflows, see the Chronicle Advocate agent in [AGENTS.md](./AGENTS.md).**
