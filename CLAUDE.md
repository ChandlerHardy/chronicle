# Chronicle - Context for AI Assistants

> **Last Updated**: October 20, 2025
> **Project Status**: Phase 3 Complete - Multi-Provider Summarization, Repo Tracking, Transcript Cleaning
> **Tests**: 16 passing (8 git + 8 AI tracking)

## 🤖 For AI Coding Assistants: How to Use Chronicle

### Quick Start

**If user asks about Chronicle or session tracking:**

```bash
# Suggest this workflow to the user:
1. Exit current session
2. Run: chronicle start claude
3. Continue working (session is now being tracked)
4. When done: exit
5. View summary: chronicle session <id>
```

### Understanding Chronicle Sessions

**Key Points:**
- Chronicle sessions are started **manually** by the user with `chronicle start claude`
- This wraps the Claude Code session and captures the full transcript
- Sessions are NOT automatically tracked - user must explicitly start tracking
- **You cannot start Chronicle from within an active session** (would create nested sessions)

### When Working in THIS Project

1. **Current session is likely NOT being tracked** - User would need to restart with `chronicle start claude`
2. **DO** use `chronicle session <id>` to view/summarize past sessions when debugging
3. **DO** use `chronicle summarize-session <id>` for large sessions (> 100KB) that need Qwen/Gemini CLI
4. **DO** query the database when debugging: `sqlite3 ~/.ai-session/sessions.db "SELECT ..."`
5. **DO NOT** run `chronicle start` from within a session

### When Working on OTHER Projects

**Suggest to the user:**
- "Would you like to track this session with Chronicle? Run `chronicle start claude` before we begin."
- After session: "You can view the summary with `chronicle session <id>`"
- Sessions auto-detect the git repository and tag themselves accordingly
- All commits made during the session are automatically linked

**Common Commands:**
```bash
chronicle sessions                    # List recent sessions
chronicle show today                  # See today's work
chronicle timeline today              # Combined commits + AI sessions
chronicle sessions --repo /path/repo  # Filter by project
```

## What Is This Project?

Chronicle is a **local-first development session recorder** that tracks interactions across multiple AI coding assistants (Claude Code, Gemini CLI, Qwen Code), git commits, and file changes to create a unified, searchable development timeline with AI-powered summarization.

### The Problem We're Solving

Modern developers use multiple AI assistants, but:
- Each AI has no memory of what other AIs did
- No persistent record between sessions
- Hard to track decisions made across different tools
- Context is lost when switching between tools

### Our Solution

Chronicle provides:
- Full AI session recording (complete transcripts)
- Git commit tracking and linking
- AI-powered summarization using Gemini
- Unified timeline across all tools
- Searchable development history
- Local-first privacy (SQLite)

## Current Architecture

### Tech Stack

**Backend**
- Python 3.11+ (core logic)
- SQLite (local storage at `~/.ai-session/sessions.db`)
- Click (CLI framework)
- Rich (terminal formatting)
- GitPython (git integration)
- SQLAlchemy (database ORM)
- PyYAML (configuration)
- Google Gemini API (AI summarization)

**Storage Locations**
- Database: `~/.ai-session/sessions.db`
- Session transcripts: `~/.ai-session/sessions/session_N.log`
- Session metadata: `~/.ai-session/sessions/session_N.meta`
- Configuration: `~/.ai-session/config.yaml`

### Project Structure

```
chronicle/
├── backend/
│   ├── main.py                 # CLI entry point
│   ├── core/
│   │   └── config.py           # Configuration management
│   ├── database/
│   │   ├── models.py           # SQLAlchemy models (commits, ai_interactions, summaries)
│   │   └── migrate.py          # Database migrations
│   ├── services/
│   │   ├── git_monitor.py      # Git commit tracking
│   │   ├── ai_tracker.py       # AI interaction logging
│   │   ├── session_manager.py  # Session recording with Unix 'script' command
│   │   └── summarizer.py       # Gemini AI summarization
│   └── cli/
│       ├── commands.py         # CLI commands implementation
│       └── formatters.py       # Rich terminal output formatting
├── tests/
│   ├── test_git_monitor.py     # 8 passing tests
│   └── test_ai_tracker.py      # 8 passing tests
├── scripts/
│   └── chronicle-ai            # Shell wrapper for AI tools
└── pyproject.toml              # Project config, dependencies
```

### Database Schema

**commits** - Git commit tracking
```sql
id, timestamp, sha, message, files_changed (JSON),
branch, author, repo_path
```

**ai_interactions** - AI tool interactions
```sql
id, timestamp, ai_tool (claude-code/gemini-cli/qwen-cli),
prompt, response_summary, duration_ms, files_mentioned (JSON),
is_session (bool), session_transcript, summary_generated (bool),
related_commit_id (foreign key to commits)
```

**daily_summaries** - AI-generated summaries
```sql
id, date, summary, topics (JSON), files_affected (JSON),
commits_count, ai_interactions_count, key_decisions (JSON)
```

## Key Features Implemented

### Phase 1: Git Tracking ✅ COMPLETE
- `chronicle init` - Initialize database
- `chronicle add-repo <path>` - Track a git repository
- `chronicle sync` - Sync commits from all tracked repos
- `chronicle show <today|yesterday|week>` - View commits
- `chronicle search <query>` - Search commit messages
- `chronicle stats <repo>` - Repository statistics

### Phase 2: AI Tracking ✅ COMPLETE

**Interactive Sessions** (full transcript capture using Unix `script` command)
- `chronicle start claude` - Start Claude Code session with recording
- `chronicle start gemini` - Start Gemini CLI session
- `chronicle start qwen` - Start Qwen CLI session
- `chronicle sessions` - List all recorded sessions
- `chronicle session <id>` - View session details

**One-Shot Commands** (for quick AI queries)
- `chronicle ask "question" --tool gemini` - Ask and log
- `chronicle ask "question" --tool qwen --log-only` - Log without calling AI

**Viewing & Statistics**
- `chronicle ai <today|yesterday|week>` - View AI interactions
- `chronicle ai-stats [--days N]` - Usage statistics with charts
- `chronicle timeline <today|yesterday|week>` - Combined commits + AI

### Phase 3: AI Summarization ✅ COMPLETE

**Configuration**
- `chronicle config --list` - View all settings
- `chronicle config <key> [value]` - Get/set config values
- Environment variable support: `GEMINI_API_KEY`
- API keys masked in display for security

**Summarization Features**
- `chronicle session <id>` - Auto-generates AI summary on first view
- `chronicle summarize today` - AI summary of today's work
- `chronicle summarize week` - AI summary of last 7 days
- Lazy loading: summaries generated on-demand, cached forever
- Analyzes both git commits and AI sessions
- Extracts key decisions, files modified, blockers

**Gemini Integration**
- Uses `google-generativeai` Python SDK
- Default model: `gemini-2.0-flash-exp` (fast, cheap)
- Intelligent prompting for structured summaries
- Markdown-formatted output

## Important Implementation Details

### Session Recording Architecture

Chronicle uses the Unix `script` command for full terminal capture:

1. **Session Start**: `chronicle start <tool>` spawns `script` command with PTY
2. **Recording**: Full terminal I/O captured to `.log` file
3. **Metadata**: Tool, timestamp, duration saved to `.meta` JSON file
4. **Database**: Row created in `ai_interactions` with `is_session=True`
5. **Exit**: Session metadata finalized, ready for summarization

### Lazy Summarization Pattern

**Why Lazy?**
- Fast session exit (no waiting for AI)
- Summaries only generated when needed
- Can work offline (view raw transcripts)

**How It Works:**
```python
# On session end
session.is_session = True
session.session_transcript = "session_5.log"
session.summary_generated = False  # NOT summarized yet
db.commit()

# On first `chronicle session 5` view
if not session.summary_generated:
    summary = summarizer.summarize_session(session)
    session.response_summary = summary
    session.summary_generated = True
    db.commit()
```

### Commit Linking Logic

AI interactions are linked to commits if:
1. Commit timestamp is within ±30 minutes of interaction
2. Commit repo is in tracked repositories
3. Uses `related_commit_id` foreign key

### Configuration System

**Dot Notation Access:**
```python
config.get("ai.gemini_api_key")  # Supports nested keys
config.set("ai.default_model", "gemini-2.0-flash-exp")
```

**Priority Order:**
1. Environment variables (e.g., `GEMINI_API_KEY`)
2. Config file (`~/.ai-session/config.yaml`)
3. Defaults (in `backend/core/config.py`)

### Multi-Project Repository Tracking (NEW)

**Auto-Detection:**
- Sessions automatically detect current working directory
- Finds git repository root by walking up directory tree
- Stores `working_directory` and `repo_path` in database

**Filtering:**
```bash
chronicle sessions --repo /path/to/project
chronicle summarize today --repo /path/to/project
chronicle timeline today --repo /path/to/project
```

**Database Schema:**
```python
# ai_interactions table
working_directory = Column(String(500))  # Where session started
repo_path = Column(String(500))          # Git repo root (if any)
```

### Multi-Provider Summarization (NEW)

**Providers:**
1. **Gemini API** (default) - Cloud, 1M token context, rate limits
2. **Ollama** - Local, unlimited, requires local installation

**Provider Selection:**
```python
# In summarizer.py
if self.provider == "gemini":
    # Use Google Gemini API
elif self.provider == "ollama":
    # Use local Ollama
```

**For Large Sessions:**
```bash
chronicle summarize-session 8              # Use Qwen CLI (2000 req/day)
chronicle summarize-session 8 --provider gemini  # Use Gemini CLI
```

This bypasses API rate limits by calling CLI tools directly with cleaned transcripts.

### Transcript Cleaning (NEW)

**Purpose:** Reduce transcript size by 40-90% before summarization

**What It Removes:**
- ANSI escape codes (e.g., `\x1B[0m`)
- CSI sequences (cursor positioning)
- Control characters (except newlines)
- Duplicate consecutive lines (spinner redraws)

**Implementation:**
```python
# In summarizer.py
def _clean_transcript(self, transcript: str) -> str:
    # Remove ANSI codes
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    cleaned = ansi_escape.sub('', transcript)

    # Deduplicate lines
    # ... (see code for full logic)

    return cleaned_transcript
```

**Results:**
- Session 8: 709KB → 336KB (52.7% reduction)
- Session 9: 826KB → 422KB (49.0% reduction)

## Development Workflow

### Running Tests
```bash
pytest                          # Run all tests
pytest --cov=backend tests/     # Run with coverage
pytest -v                       # Verbose output
```

### Local Development
```bash
# Install in editable mode
pip install -e .

# Run CLI
chronicle --help

# Test individual commands
chronicle init
chronicle add-repo .
chronicle show today
```

### Code Style
- Black formatting (line length 100)
- Ruff linting
- Type hints where beneficial
- Comprehensive docstrings

## Common Tasks for AI Assistants

### Adding a New CLI Command

1. Add command function to `backend/cli/commands.py`
2. Use `@cli.command()` decorator
3. Import formatters from `backend/cli/formatters.py`
4. Add tests to `tests/test_*.py`

### Adding a New AI Tool

1. Update `backend/services/ai_tracker.py` to handle new tool
2. Add tool name to database schema if needed
3. Update `backend/cli/formatters.py` for tool-specific emoji/styling
4. Test with wrapper: `chronicle start <new-tool>`

### Modifying Database Schema

1. Update models in `backend/database/models.py`
2. Add migration logic to `backend/database/migrate.py`
3. Test migration with fresh database
4. Update tests

### Adding New Configuration Options

1. Add default to `backend/core/config.py` in `_create_default_config()`
2. Add property accessor if needed
3. Document in README.md
4. Update config command help text

## Testing Philosophy

**Current Coverage:**
- Git monitoring: 8 tests (repository scanning, commit tracking, search, stats)
- AI tracking: 8 tests (logging, session management, timeline, statistics)
- Total: 16 passing tests

**Test Approach:**
- Use pytest fixtures for database setup
- Test with temporary directories for git repos
- Mock external API calls (Gemini)
- Test both success and error cases

## Known Limitations

1. **Session recording only works on Unix-like systems** (uses `script` command)
   - Linux: ✅ Works
   - macOS: ✅ Works
   - Windows: ❌ Not supported (could use PowerShell transcript in future)

2. **Gemini API required for summarization** (free tier available)
   - All other features work offline

3. **Git repositories must have commits** to track
   - Empty repos show no data until first commit

4. **Session wrapper requires AI CLIs to be installed**
   - `claude` command for Claude Code
   - `gemini` command for Gemini CLI
   - `qwen` command for Qwen CLI

## Future Enhancements (Phase 4+)

**Next Up:**
- [ ] Next.js web dashboard
- [ ] Timeline visualization
- [ ] Export to Markdown/JSON/PDF
- [ ] Blog post generator
- [ ] Auto-update CLAUDE.md from sessions

**Future Ideas:**
- VS Code extension
- Slack bot for daily summaries
- GitHub action for PR descriptions
- Team collaboration features
- Knowledge graph of file relationships

## Debugging Tips

**Check database**
```bash
sqlite3 ~/.ai-session/sessions.db
.tables
.schema commits
SELECT * FROM ai_interactions LIMIT 5;
```

**View session transcript**
```bash
cat ~/.ai-session/sessions/session_5.log
```

**Check config**
```bash
chronicle config --list
cat ~/.ai-session/config.yaml
```

**Verbose output**
```bash
# Add debug prints to backend/services/*.py
# Run with Python directly
python -m backend.main show today
```

## Important Conventions

### Emojis in Output
- 🎯 Claude Code
- ✨ Gemini CLI
- 🔮 Qwen CLI
- 📊 Statistics
- 🔍 Search
- ✅ Success
- ❌ Error

### Time Windows
- "today" = last 24 hours
- "yesterday" = 24-48 hours ago
- "week" = last 7 days
- Commit linking window = ±30 minutes

### Date Formatting
- Display: "October 19, 2025 02:30 PM"
- Database: ISO 8601 timestamps
- Rich output: Relative times when helpful ("2 hours ago")

## File Locations Reference

**Critical Files:**
- `backend/main.py` - CLI entry point, all commands registered here
- `backend/database/models.py` - SQLAlchemy models, schema definitions
- `backend/services/summarizer.py` - Gemini integration, prompt engineering
- `backend/cli/formatters.py` - All Rich terminal formatting logic
- `backend/core/config.py` - Configuration management

**Configuration:**
- `~/.ai-session/config.yaml` - User configuration
- `pyproject.toml` - Project metadata, dependencies, scripts

**Data:**
- `~/.ai-session/sessions.db` - Main SQLite database
- `~/.ai-session/sessions/` - Session transcript files

## Success Criteria

Chronicle is successful if it:
- ✅ Captures 95%+ of git commits (ACHIEVED)
- ✅ Logs AI interactions with <100ms overhead (ACHIEVED)
- ✅ Can answer "what did I do yesterday?" in <5 seconds (ACHIEVED)
- ✅ Finds specific past decisions in <10 seconds (ACHIEVED)
- ✅ Provides context across AI sessions (ACHIEVED)
- ✅ Generates useful summaries automatically (ACHIEVED - Phase 3)
- ⏳ Database size stays under 50MB/year (IN PROGRESS)

## Getting Help

**Documentation:**
- Full spec: `AI_SESSION_RECORDER_SPEC.md`
- Changelog: `CHANGELOG.md`
- This file: `CLAUDE.md`

**Key Commands:**
```bash
chronicle --help                 # List all commands
chronicle <command> --help       # Command-specific help
pytest -v                        # Run tests
```

---

**When working on Chronicle, remember:**
1. All features are local-first (privacy matters!)
2. Tests must pass before committing
3. Rich terminal output should be beautiful and informative
4. Configuration should have sensible defaults
5. Error messages should be helpful, not cryptic
6. This tool tracks itself - dogfooding is real!

**Chronicle is meta**: We use Chronicle to track building Chronicle. Check the database for examples of real usage!
