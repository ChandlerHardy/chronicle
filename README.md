# Chronicle - AI Session Recorder

> **Track your AI-assisted development sessions across multiple tools, capture decisions, and never lose context.**

A local-first development session recorder that tracks interactions across multiple AI coding assistants (Claude Code, Gemini CLI, Qwen Code), git commits, and file changes to create a unified, searchable development timeline.

[![Tests](https://img.shields.io/badge/tests-16%20passing-brightgreen)]()
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)]()
[![License](https://img.shields.io/badge/license-MIT-blue)]()

---

## 🎯 The Problem

Modern developers use multiple AI coding assistants, but:
- ❌ Each AI has no memory of what other AIs did
- ❌ No persistent record between sessions
- ❌ Hard to track decisions made across different tools
- ❌ Context is lost when switching between Claude Code, Gemini CLI, Qwen Code
- ❌ "What did we decide about authentication 2 weeks ago?" 🤷

## ✨ The Solution

Chronicle is a **local-first session recorder** that:
- ✅ **Records full AI sessions** - Capture complete conversations with Claude Code, Gemini CLI, Qwen Code
- ✅ **Tracks git commits** - Link commits to the AI sessions that created them
- ✅ **Unified timeline** - See what ALL your AI tools did, in one place
- ✅ **Searchable history** - Query past decisions, conversations, and changes
- ✅ **Lazy summarization** - AI-powered summaries with Gemini (generated on-demand)
- ✅ **Privacy-first** - Everything stored locally in SQLite

---

## 🚀 Quick Start

### Installation

```bash
# Clone and install
git clone https://github.com/ChandlerHardy/chronicle
cd chronicle
python3 -m pip install -e .

# Initialize Chronicle
chronicle init

# Configure Gemini API for summarization (optional)
chronicle config ai.gemini_api_key YOUR_API_KEY

# Add a repository to track
chronicle add-repo /path/to/your/project
```

### Basic Usage

```bash
# View today's activity (commits + AI interactions)
chronicle show today

# Start an interactive AI session (auto-recorded)
chronicle start claude      # Claude Code
chronicle start gemini      # Gemini CLI
chronicle start qwen        # Qwen Code CLI

# View all sessions
chronicle sessions

# See combined timeline
chronicle timeline today

# Search history
chronicle search "authentication"
```

---

## 📖 Core Concepts

### Chronicle vs CLAUDE.md

**CLAUDE.md** is static project documentation:
- ✅ Project structure, conventions, tech stack
- ✅ Written manually, read by AI at session start
- ✅ Describes "how this project works"

**Chronicle** is dynamic session recording:
- ✅ Automatic tracking of what you actually did
- ✅ Cross-AI session history (Claude, Gemini, Qwen)
- ✅ Searchable timeline of decisions and changes
- ✅ Describes "what happened and why"

**They're complementary!** CLAUDE.md tells the AI about your project, Chronicle tells YOU what you did.

---

## 🎮 Features

### ✅ Phase 1: Git Commit Tracking (COMPLETE)

Track git commits and link them to development activity:

```bash
chronicle add-repo /path/to/project    # Import commits
chronicle show today                    # View today's commits
chronicle search "bug fix"              # Search commit messages
chronicle stats /path/to/project        # Repository statistics
```

**Features:**
- Auto-scan git repositories for commits
- Store commit metadata (SHA, message, files, author, timestamp)
- Prevent duplicates
- Search by message content
- Filter by date range

---

### ✅ Phase 2: AI Interaction Tracking (COMPLETE)

#### Interactive Session Wrapper

Record full AI coding sessions with transcript capture:

```bash
chronicle start claude      # Start Claude Code session
chronicle start gemini      # Start Gemini CLI session
chronicle start qwen        # Start Qwen Code CLI session

# Work normally in the AI tool...
# Full transcript is recorded automatically

exit                        # Session saved!

chronicle sessions          # List all sessions
chronicle session 5         # View session details
```

**Features:**
- Full terminal transcript capture using Unix `script` command
- Records all input/output from AI conversations
- Automatic timestamp tracking
- Session duration calculation
- Lazy summarization (transcript saved immediately, summary generated on-demand)

#### One-Shot AI Commands

For quick questions to Gemini or Qwen:

```bash
chronicle ask "How do I optimize this query?" --tool gemini
chronicle ask "Review this code for bugs" --tool qwen
chronicle ask "Test question" --tool gemini --log-only
```

#### CLI Commands

```bash
chronicle ai today              # View today's AI interactions
chronicle ai yesterday          # Yesterday's interactions
chronicle ai week               # Last 7 days

chronicle ai-stats              # Usage statistics with charts
chronicle ai-stats --days 30    # Last 30 days

chronicle timeline today        # Combined commits + AI interactions
```

**Features:**
- AI interaction logging (prompt, response, duration)
- Auto-link interactions to commits (30-minute window)
- Multi-tool support (Claude Code, Gemini CLI, Qwen Code)
- Beautiful terminal output with tool-specific emojis (🎯 Claude, ✨ Gemini, 🔮 Qwen)
- Usage statistics with visual charts

---

### 🔧 Configuration System (COMPLETE)

Manage Chronicle settings with YAML config:

```bash
chronicle config --list                          # View all settings
chronicle config ai.gemini_api_key              # View API key (masked)
chronicle config ai.gemini_api_key YOUR_KEY     # Set API key
chronicle config ai.default_model               # View default model
```

**Config file:** `~/.ai-session/config.yaml`

**Available settings:**
- `ai.gemini_api_key` - Gemini API key for summarization
- `ai.default_model` - Default Gemini model (gemini-2.5-flash)
- `ai.auto_summarize_sessions` - Auto-summarize on session exit
- `retention.raw_data_days` - How long to keep raw transcripts (7 days)
- `retention.summaries_days` - How long to keep summaries (90 days)

**Security:**
- API keys masked in display
- Environment variable support (`GEMINI_API_KEY`)
- Config file excluded from git (`.gitignore`)

---

### 🤖 Gemini Integration (Phase 3 Preview)

AI-powered summarization with Google Gemini:

```bash
chronicle test-gemini           # Test API connection
chronicle config ai.gemini_api_key YOUR_KEY
chronicle config ai.default_model gemini-2.5-flash
```

**Coming in Phase 3:**
- `chronicle summarize` - Generate summaries for sessions/days
- Automatic session summarization on first view
- Topic extraction from conversations
- Weekly digest generation

---

## 📊 Example Outputs

### Daily Summary

```bash
$ chronicle show today

Development Session - October 19, 2025
════════════════════════════════════════════════════════════
╭──────────────────────────────────────────────────────────╮
│ Session Statistics                                       │
│ • Commits: 5                                             │
│ • Files Changed: 12                                      │
│ • Repositories: 2                                        │
│ • Authors: 1                                             │
╰──────────────────────────────────────────────────────────╯

Commits
────────────────────────────────────────────────────────────
10:30 AM [abc1234] Add user authentication
   → src/auth.ts
   → src/middleware.ts

02:15 PM [def5678] Update README with usage examples
   → README.md
```

### AI Interaction Timeline

```bash
$ chronicle ai today

AI Interactions Today
────────────────────────────────────────────────────────────
02:30 PM ✨ Gemini
   "How do I implement caching in Python?"
   → You can use functools.lru_cache decorator...
   ⏱ 2.3s
   ✓ Linked to commit abc1234

01:45 PM 🔮 Qwen
   "Review this authentication code"
   → The code looks good overall. Consider adding rate limiting...
   ⏱ 3.1s
```

### AI Usage Statistics

```bash
$ chronicle ai-stats --days 7

AI Tool Usage (Last 7 days)
════════════════════════════════════════════════════════════
┏━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┓
┃ AI Tool  ┃  Interactions ┃   Percentage ┃  Avg Duration ┃
┡━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━┩
│ Claude   │            15 │        65.2% │         4.2s  │
│          │               │ █████████░░░ │               │
│ Gemini   │             6 │        26.1% │         2.1s  │
│          │               │ █████░░░░░░░ │               │
│ Qwen     │             2 │         8.7% │         3.5s  │
│          │               │ █░░░░░░░░░░░ │               │
└──────────┴───────────────┴──────────────┴───────────────┘

Total interactions: 23
```

### Combined Timeline

```bash
$ chronicle timeline today

Combined Development Timeline
════════════════════════════════════════════════════════════
02:30 PM ✨ Gemini
   "How do I implement caching in Python?"

02:25 PM [abc1234] Add caching to API endpoints
   → api/cache.py
   → api/endpoints.py

01:45 PM 🎯 Claude (Session, 45m)
   "Built authentication system"
   → src/auth.ts
   → src/middleware.ts
   ✓ Linked to commit def5678

01:30 PM [def5678] Implement JWT authentication
   → auth/jwt.ts
```

---

## 🗂️ Database Schema

Chronicle uses SQLite for local-first storage at `~/.ai-session/sessions.db`:

### Tables

**commits** - Git commit tracking
- timestamp, SHA, message, files_changed (JSON)
- branch, author, repo_path

**ai_interactions** - AI tool interactions
- timestamp, ai_tool, prompt, response_summary
- duration_ms, files_mentioned (JSON)
- is_session, session_transcript, summary_generated
- related_commit_id (foreign key)

**daily_summaries** - Daily development summaries (Phase 3)
- date, summary, topics (JSON), files_affected (JSON)
- commits_count, ai_interactions_count, key_decisions (JSON)

### Data Storage

- **Database:** `~/.ai-session/sessions.db`
- **Session transcripts:** `~/.ai-session/sessions/session_N.log`
- **Session metadata:** `~/.ai-session/sessions/session_N.meta`
- **Configuration:** `~/.ai-session/config.yaml`

---

## 🧪 Testing

Chronicle has comprehensive test coverage:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=backend tests/

# Current status: 16 passing tests
# - 8 tests for git monitoring
# - 8 tests for AI tracking
```

---

## 🛣️ Roadmap

### ✅ Phase 1: Git Tracking (COMPLETE)
- [x] Git commit monitoring
- [x] CLI query interface
- [x] Search and statistics
- [x] 8 passing tests

### ✅ Phase 2: AI Tracking (COMPLETE)
- [x] AI interaction logging
- [x] Session wrapper for Claude/Gemini/Qwen
- [x] Multi-AI timeline view
- [x] Usage statistics
- [x] Configuration system
- [x] 8 passing tests

### 🔜 Phase 3: Summarization (NEXT)
- [ ] Gemini API integration complete
- [ ] `chronicle summarize` command
- [ ] Daily summary generation
- [ ] Topic extraction
- [ ] Data retention policies

### 📋 Phase 4: Dashboard (PLANNED)
- [ ] Next.js web interface
- [ ] Timeline visualization
- [ ] Export features (Markdown, JSON)
- [ ] Blog post generator

---

## 🏗️ Architecture

### Local-First Design

Chronicle is designed to be **private and fast**:
- ✅ All data stored in local SQLite database
- ✅ No cloud sync required (optional in future)
- ✅ Works offline
- ✅ Full control over your data

### Lazy Summarization

Sessions are recorded immediately, summaries generated on-demand:

```
Session Start
    ↓
Record full transcript → Save to DB (fast!)
    ↓
On first view → Generate summary with Gemini
    ↓
Cache summary for future views
```

**Benefits:**
- Fast session exit (no waiting for summarization)
- Summaries only generated when needed
- Can work offline (view raw transcripts)

---

## 🤝 Contributing

Chronicle is open source! Contributions welcome.

**Ideas for contributions:**
- Add support for more AI CLIs (Cursor, Copilot, etc.)
- Build the Phase 3 summarization features
- Create the Next.js dashboard
- Improve test coverage
- Add export formats (Markdown, JSON, PDF)

---

## 📝 License

MIT License - see [LICENSE](LICENSE)

---

## 🙏 Acknowledgments

**Built with:**
- [Claude Code](https://claude.com/claude-code) - AI coding assistant (and tracked by Chronicle itself! 🎯)
- [Google Gemini](https://ai.google.dev/) - AI summarization
- Python 3.11+ - Core logic
- SQLite - Local storage
- Click - CLI framework
- Rich - Terminal formatting
- GitPython - Git integration

---

## 📚 Documentation

- [Project Specification](AI_SESSION_RECORDER_SPEC.md) - Full specification and roadmap
- [Changelog](CHANGELOG.md) - Version history
- [Example Context](example/CLAUDE.md) - Example from Crooked Finger project

---

**Chronicle: Never lose context again.** 🎯

*Track your AI-assisted development journey, compare approaches, and build institutional knowledge across all your AI coding assistants.*
