# Changelog

All notable changes to Chronicle will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2025-10-19

### Phase 2: AI Interaction Tracking - COMPLETE ✅

#### Added
- **AI Interaction Tracking Service** (`backend/services/ai_tracker.py`)
  - Log AI tool interactions with prompts, responses, and duration
  - Auto-link interactions to commits within 30-minute window
  - Search and filter by AI tool and date range
  - Generate usage statistics

- **Shell Wrapper Script** (`scripts/chronicle-ai`)
  - Intercept AI CLI tool calls (Gemini, Qwen)
  - Automatic logging with timing
  - Pass-through to actual CLI tools
  - Background logging for minimal overhead

- **New CLI Commands**
  - `chronicle ai <today|yesterday|week>` - View AI interaction history
  - `chronicle ai-stats [--days N]` - AI tool usage statistics with charts
  - `chronicle timeline <today|yesterday|week>` - Combined commits + AI view
  - `chronicle ask <prompt> --tool <gemini|qwen>` - Ask and auto-log
  - `--tool` filter for AI commands
  - `--log-only` flag for testing

- **Beautiful Terminal Output**
  - Tool-specific emojis (✨ Gemini, 🔮 Qwen, 🎯 Claude)
  - Rich tables for statistics
  - Visual percentage bars
  - Duration tracking display
  - Linked commit indicators

- **Database Schema**
  - `ai_interactions` table with full relationship to commits
  - JSON storage for files_mentioned
  - Response truncation to 500 chars

- **Tests**
  - 8 comprehensive tests for AI tracking (`tests/test_ai_tracker.py`)
  - Coverage: logging, search, stats, commit linking, date filtering

#### Changed
- Enhanced formatters with AI interaction support
- Updated README with Phase 2 documentation
- Updated spec with progress tracking

## [0.1.0] - 2025-10-19

### Phase 1: Git Commit Tracking - COMPLETE ✅

#### Added
- **Project Setup**
  - Python package structure with `pyproject.toml`
  - SQLite database initialization
  - Click-based CLI framework
  - Rich terminal formatting

- **Git Monitoring Service** (`backend/services/git_monitor.py`)
  - Scan repositories for commits
  - Store commit metadata (SHA, message, files, author, timestamp)
  - Prevent duplicate tracking
  - Search commits by message
  - Filter by date ranges
  - Repository statistics

- **CLI Commands**
  - `chronicle init` - Initialize Chronicle
  - `chronicle add-repo <path>` - Add repository to track
  - `chronicle show <today|yesterday|week>` - View activity
  - `chronicle search <term>` - Search commit messages
  - `chronicle stats <path>` - Repository statistics
  - `chronicle sync <path>` - Sync new commits

- **Database Schema**
  - `commits` table with full metadata
  - `ai_interactions` table (schema ready)
  - `daily_summaries` table (schema ready)
  - SQLAlchemy ORM models

- **Terminal Output**
  - Rich panels and tables
  - Color-coded output
  - Session statistics
  - Formatted commit lists with file changes

- **Tests**
  - 8 passing tests for git monitoring (`tests/test_git_monitor.py`)
  - Coverage: scanning, duplicates, search, stats, error handling

- **Documentation**
  - Comprehensive README with examples
  - Project specification document
  - Installation instructions
  - Usage examples

#### Technical Details
- Python 3.11+ with type hints
- SQLite for local-first storage (~/.ai-session/)
- GitPython for git operations
- Click for CLI
- Rich for beautiful terminal output
- Pytest for testing

---

## Upcoming

### Phase 3: Summarization (Next)
- [ ] Gemini API integration
- [ ] Daily summary generation
- [ ] Weekly digest creation
- [ ] Data retention policies
- [ ] Topic extraction
- [ ] `chronicle summarize` command

### Phase 4: Dashboard (Future)
- [ ] Next.js web interface
- [ ] Timeline visualization
- [ ] Export features (Markdown, JSON)
- [ ] Blog post generation
- [ ] Auto-update CLAUDE.md

---

**Note**: Chronicle is being used to document its own development! 🎯
