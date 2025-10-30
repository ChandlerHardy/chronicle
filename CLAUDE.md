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

## 🚨 CRITICAL: SEARCH FIRST (MANDATORY)

**BEFORE IMPLEMENTING ANYTHING, YOU MUST SEARCH CHRONICLE:**

```python
mcp__chronicle__search_sessions(query="relevant keywords", limit=10)
```

**WHY THIS IS MANDATORY:**
- Searching: **1 second**
- Reinventing: **10-20 minutes**
- **ROI: 2,700x** (proven from Sessions 21, 30, 31 - 45+ minutes wasted)

**This is not optional. This is not a suggestion. Search first, ALWAYS.**

---

## 🔧 Working on Chronicle (The Meta Project)

**Chronicle is meta:** It tracks its own development.

**Key differences when working on Chronicle vs using Chronicle:**
1. **Dogfooding:** Every session you run is tracked, every mistake is in the database
2. **Search first:** Past sessions contain solutions to problems you might encounter
3. **MCP server restart required:** After changing `backend/mcp/server.py`, restart Claude Code
4. **Test with Chronicle:** Use `chronicle start claude` to track your development work

### Core Directives (MANDATORY - Apply Even With Chronicle Advocate Available)

**YOU MUST FOLLOW THESE DIRECTIVES FOR EVERY INTERACTION:**

#### 1. 🔍 SEARCH FIRST (MANDATORY)

**ALWAYS search Chronicle before implementing or modifying anything:**

```python
mcp__chronicle__search_sessions(query="relevant keywords", limit=10)
```

**Why this is mandatory:**
- ❌ Not searching → Reimplementing features, breaking working code, wasting 10-20 minutes
- ✅ Searching → Finding past solutions in <1 second, understanding WHY decisions were made
- **Proven ROI: 2,700x** (Sessions 21, 30, 31 - 45+ minutes wasted by not searching)

**Trigger phrases that REQUIRE searching:**
- User says "I can't believe..." → Search first!
- User says "why isn't..." → Search first!
- User says "this should work..." → Search first!
- Before adding any feature → Check if it exists
- When debugging → Check past sessions for similar issues

**Real example from Session 21:**
```
User: "I can't believe there's no cleaning to be done on session 21"
❌ Without search: Spent 15+ minutes debugging, confused why 0% reduction
✅ With search: Would have found Session 13 implemented transcript cleaning
  → Result: Immediately understood cleaning happens at storage time
```

#### 2. ✍️ WRITE TESTS FIRST (MANDATORY - TDD)

**NEVER write implementation code without tests:**

```python
# ❌ WRONG: Writing implementation first
def export_session(session_id):
    # ... implementation ...

# ✅ CORRECT: Writing test first (red-green-refactor)
def test_export_session_with_file_fallback():
    # ... test that fails ...
    # THEN write implementation to make it pass
```

**When you MUST write tests:**
- Before implementing new features
- Before fixing bugs (write failing test that reproduces bug)
- Before refactoring (ensure tests pass before AND after)
- When user asks "why don't you write tests??" (you violated this!)

**Real violations from this project:**
- Session 52: Created 4 CLI commands WITHOUT tests → User called out violation
- Session 52: Implemented file fallback WITHOUT tests → User called out violation again
- **Never repeat these mistakes**

#### 3. 📊 CHECK SESSION STATUS (REQUIRED)

**Verify if current session is being tracked:**
```python
# Check if conversation is being tracked
status = mcp__chronicle__get_current_session()
# Returns: {"active": true, "session": {...}} or {"active": false}
```

**If not tracking:**
- Current session NOT tracked unless started with `chronicle start claude`
- **YOU MUST suggest exit and restart if meaningful work is happening**
- User can verify with: `chronicle status` command

#### 4. ⚡ USE MCP OVER CLI (MANDATORY)

**Always prefer MCP tools, NEVER use CLI for programmatic access:**

```python
# ✅ CORRECT (MCP - fast, structured JSON):
sessions = mcp__chronicle__search_sessions(query="storage", limit=5)
roadmap = mcp__chronicle__get_roadmap(days=7)

# ❌ WRONG (CLI - slow, hard to parse):
Bash("chronicle search 'storage'")
Bash("chronicle roadmap")
```

**Why MCP over CLI:**
- **Speed**: MCP queries DB directly (<10ms), CLI spawns subprocess (>100ms)
- **Programmatic**: Returns structured JSON, not formatted text
- **Reliable**: No parsing of human-readable output

#### 5. 🗺️ CHECK ROADMAP BEFORE PLANNING (REQUIRED)

**Avoid duplicate work:**
```python
mcp__chronicle__get_roadmap(days=7)
mcp__chronicle__get_next_steps(completed=False)
```

**Failure to check roadmap can result in duplicating already-planned work**

#### 6. 🏷️ SUGGEST SESSION ORGANIZATION (REQUIRED)

**After significant work:**
- YOU MUST propose descriptive title
- YOU MUST suggest relevant tags (technologies, features, bugs)
- YOU MUST link to related sessions

---

**For deep analysis and enforcement:** Launch the Chronicle Advocate agent (see [AGENTS.md](./AGENTS.md))

---

## 🎯 Chronicle Skills (Use These First!)

**BEFORE manually calling MCP tools, check if a skill exists for the task:**

| Task | Use This Skill | Instead of Manual |
|------|----------------|-------------------|
| 📝 Export session to Obsidian | `chronicle-session-documenter` | Manual `mcp__chronicle__get_session_summary()` + `mcp__obsidian__write_note()` calls |
| 🔍 Search past sessions for context | `chronicle-context-retriever` | Manual search and analysis across multiple sessions |
| 🔄 Complete Chronicle workflow guidance | `chronicle-workflow` | Ad-hoc workflow instructions |
| 📊 Manage milestones and roadmap | `chronicle-project-tracker` | Manual milestone/next step operations |

### How to Invoke Skills

**Method 1: Let skill auto-activate (preferred)**
```
User: "Export session 75 to Obsidian"
→ Skill should auto-activate based on description match
→ Follow skill's guidance
```

**Method 2: Explicit invocation**
```python
Skill(command="chronicle-session-documenter")
→ Skill loads and provides detailed instructions
→ Follow the workflow it describes
```

### Why Use Skills Over Manual MCP Calls?

- ✅ **Complete workflows** - Skills guide through entire process, not just one MCP call
- ✅ **Best practices** - Skills encode correct patterns (formatting, error handling, etc.)
- ✅ **Consistency** - Same structured output every time
- ✅ **Examples** - Skills include usage examples and common patterns
- ✅ **Maintenance** - Update skill once, all uses benefit

### Skill Locations

- **User skills:** `~/.claude/plugins/marketplaces/chronicle-skills/chronicle-skills/`
- **Project skills:** `chronicle-skills/` (for plugin marketplace)

**Available skills documented in:** `chronicle-skills/README.md`

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

**Small/Medium Sessions (<50K lines):**
1. **gemini-2.5-flash** - 250K TPM, 250 RPD - Latest stable features (preferred)
2. **gemini-2.5-flash-preview-09-2025** - 250K TPM, 250 RPD - Preview features
3. **gemini-2.0-flash** - 1M TPM, 200 RPD - Fallback (overkill for small sessions)
4. **gemini-2.0-flash-lite** - 1M TPM, 200 RPD - Additional fallback
5. **gemini-2.5-flash-lite** - 250K TPM, 1000 RPD - High volume fallback

**Large Sessions (>50K lines):**
1. **gemini-2.0-flash** - 1M TPM, 200 RPD - Primary (handles 10K line chunks)
2. **gemini-2.0-flash-lite** - 1M TPM, 200 RPD - First fallback (same capacity)
3. **gemini-2.5-flash** - 250K TPM, 250 RPD - **Reduces chunks to 5K lines** for 250K TPM
4. **gemini-2.5-flash-preview-09-2025** - 250K TPM, 250 RPD
5. **gemini-2.5-flash-lite** - 250K TPM, 1000 RPD

**Why Vary by Size:**
- **Small/medium**: 2.5 models have latest features, 250K TPM is sufficient for 3-5K line chunks
- **Large**: 2.0 models have 1M TPM (4x more), enabling 10K line chunks for faster processing
- **Automatic chunk size adjustment**: When large sessions fall back to 2.5 models, chunk size reduces from 10K→5K to fit within 250K TPM
- **Smart failover**: Tracks usage per model in database for intelligent selection

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

### 🚨 PRE-FLIGHT CHECKLIST (DO THIS FIRST!)

**Before starting ANY development task, run this checklist:**

1. **SEARCH CHRONICLE** (1 second, saves 10-20 minutes):
   ```python
   mcp__chronicle__search_sessions(query="<your task>", limit=10)
   ```

2. **CHECK ROADMAP** (avoid duplicate planning):
   ```python
   mcp__chronicle__get_roadmap(days=7)
   mcp__chronicle__get_next_steps(completed=False)
   ```

3. **WRITE TESTS FIRST** (TDD red-green-refactor):
   - Write failing test
   - Implement feature to make test pass
   - Refactor

**Violating this checklist wastes time and frustrates the user. Follow it religiously.**

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

---

## 🔗 Quick Links

- Database: `~/.ai-session/sessions.db`
- Sessions: `~/.ai-session/sessions/`
- Config: `~/.ai-session/config.yaml`
- MCP config: `~/.mcp.json`

---

## ⚠️ Common Mistakes to Avoid

**Learn from real violations in this project:**

### Mistake #1: Not Searching Chronicle First

**Real example from Session 52:**
```
User: "oh right! we stopped storing transcripts in the db a while back.
       why didn't you check chronicle??"

❌ What I did: Implemented file fallback without searching
✅ What I should have done:
   mcp__chronicle__search_sessions(query="transcript storage", limit=10)
   → Would have found Milestone #2 documenting the change
```

**Impact**: Wasted 20+ minutes debugging, user had to remind me

### Mistake #2: Writing Code Without Tests

**Real example from Session 52:**
```
User: "what does the tdd advocate say about it all? it seems you haven't
       been checking CLAUDE.md or chronicle, why is that?"

❌ What I did: Created 4 CLI commands (export/import) without any tests
✅ What I should have done: Write tests FIRST for each command
   → TDD advocate had to be launched to fix the violation
```

**Impact**: Had to write 17 tests retroactively, added extra work

### Mistake #3: Using CLI Instead of MCP

**Real pattern to avoid:**
```python
# ❌ WRONG (slow, hard to parse):
output = Bash("chronicle sessions")
sessions = parse_table_output(output)  # Fragile!

# ✅ CORRECT (fast, structured):
sessions = mcp__chronicle__get_sessions(limit=10)
# Returns clean JSON, 10x faster
```

### Mistake #4: Not Checking Roadmap

**Pattern to avoid:**
```
User: "I want to add export functionality"
❌ Start implementing immediately
✅ Check roadmap first: mcp__chronicle__get_roadmap(days=7)
   → Might already be planned or partially implemented
```

---

## 🎯 Final Reminder

**Before you finish reading this file and start working:**

1. **SEARCH CHRONICLE FIRST** - `mcp__chronicle__search_sessions(query="...", limit=10)`
2. **CHECK ROADMAP** - `mcp__chronicle__get_roadmap(days=7)`
3. **WRITE TESTS FIRST** - TDD red-green-refactor cycle
4. **VERIFY SESSION TRACKING** - `mcp__chronicle__get_current_session()` to check if active

**This is mandatory. Every single time. No exceptions.**

**If you hear trigger phrases ("I can't believe...", "why isn't..."), STOP and search Chronicle.**

---

**For universal Chronicle directives and workflows, see the Chronicle Advocate agent in [AGENTS.md](./AGENTS.md).**
