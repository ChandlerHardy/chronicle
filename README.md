# AI Session Recorder (Chronicle)

A development session recorder that tracks interactions across multiple AI tools, git commits, and file changes to create a unified development timeline with intelligent summarization.

## Problem Statement

Modern developers use multiple AI assistants, but:
- Each AI has no memory of what other AIs did
- No persistent record between sessions
- Hard to track decisions made across different tools
- Documentation becomes outdated quickly

## Solution

Chronicle is a local-first session recorder that:
1. Monitors AI interactions across multiple tools
2. Tracks git commits and file changes
3. Generates intelligent summaries at multiple time scales
4. Provides queryable development history
5. Auto-generates documentation

## Installation

```bash
# Clone the repository
git clone https://github.com/ChandlerHardy/chronicle
cd chronicle

# Install in development mode
python3 -m pip install -e .
```

## Quick Start

```bash
# Initialize the recorder
chronicle init

# Add a repository to track
chronicle add-repo /path/to/your/project

# View today's activity
chronicle show today

# Search for specific commits
chronicle search "authentication"

# View repository statistics
chronicle stats /path/to/your/project

# Track AI interactions (requires gemini or qwen CLI installed)
chronicle ask "How do I optimize database queries?" --tool gemini

# View AI interaction history
chronicle ai today

# See combined timeline
chronicle timeline today
```

## Using the AI Wrapper

Chronicle includes a shell wrapper that logs AI interactions automatically. You have two options:

### Option 1: Use `chronicle ask` (Recommended)
```bash
chronicle ask "Your question here" --tool gemini
chronicle ask "Review this code" --tool qwen
```

### Option 2: Use the wrapper script directly
```bash
# Add to your PATH or create aliases
export PATH="$PATH:/path/to/chronicle/scripts"

# Then use directly
chronicle-ai gemini "Your question here"
chronicle-ai qwen "Review this code"
```

### Option 3: Test mode (log without executing)
```bash
# Great for testing or manual logging
chronicle ask "Test question" --tool gemini --log-only
```

## Available Commands

### `chronicle init`
Initialize Chronicle and create the SQLite database.

### `chronicle add-repo <path>`
Add a git repository to track. This will scan and import recent commits.

**Options:**
- `--limit`: Number of recent commits to import (default: 50)

### `chronicle show <action>`
Show development activity.

**Actions:**
- `today`: Show today's commits with summary statistics
- `yesterday`: Show yesterday's commits
- `week`: Show commits from the last 7 days

**Options:**
- `--repo`: Filter by repository path

### `chronicle search <term>`
Search commits by message content.

### `chronicle stats <path>`
Show statistics for a repository (total commits, authors, latest commit).

### `chronicle sync <path>`
Sync a repository to capture new commits since last scan.

**Options:**
- `--limit`: Number of recent commits to scan (default: 50)

### `chronicle ai <action>`
Show AI interaction history.

**Actions:**
- `today`: Show today's AI interactions
- `yesterday`: Show yesterday's AI interactions
- `week`: Show interactions from the last 7 days

**Options:**
- `--tool`: Filter by AI tool (gemini, qwen, claude)

### `chronicle ai-stats`
Show AI tool usage statistics with visual charts.

**Options:**
- `--days`: Number of days to analyze (default: 30)

### `chronicle timeline <action>`
Show combined timeline of git commits and AI interactions.

**Actions:**
- `today`: Today's combined activity
- `yesterday`: Yesterday's combined activity
- `week`: Last 7 days combined activity

**Options:**
- `--repo`: Filter commits by repository path

### `chronicle ask <prompt>`
Ask an AI tool a question and automatically log the interaction.

**Options:**
- `--tool`: AI tool to use (gemini, qwen) [required]
- `--log-only`: Only log, don't execute (for testing)

## Current Status

**Phase 1: MVP - Git Commit Tracking** ✅ COMPLETE

- [x] Python project structure
- [x] SQLite database with schema
- [x] Git commit monitoring
- [x] Basic CLI with show/search/stats commands
- [x] Rich terminal output formatting

**Phase 2: AI Interaction Tracking** ✅ COMPLETE

- [x] Shell wrapper for AI CLI tools
- [x] AI interaction database schema
- [x] Link AI interactions to commits
- [x] CLI commands for viewing AI history
- [x] Combined timeline view
- [x] AI usage statistics with charts

**Phase 3: Summarization** (Planned)

- [ ] Gemini API integration
- [ ] Daily summarization
- [ ] Weekly digests
- [ ] Data retention policies

## Tech Stack

- **Python 3.11+** - Core logic and CLI
- **SQLite** - Local data storage
- **Click** - CLI framework
- **Rich** - Terminal formatting
- **GitPython** - Git integration
- **SQLAlchemy** - Database ORM

## Data Storage

All data is stored locally at `~/.ai-session/`:
- `sessions.db` - SQLite database with all tracked data
- `config.yaml` - Configuration (coming soon)

## Database Schema

### Commits Table
```sql
CREATE TABLE commits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    sha TEXT NOT NULL,
    message TEXT NOT NULL,
    files_changed TEXT,  -- JSON array
    branch TEXT,
    author TEXT,
    repo_path TEXT
);
```

## Development

```bash
# Install development dependencies
python3 -m pip install -e ".[dev]"

# Run tests
pytest

# Format code
black backend/

# Lint code
ruff check backend/
```

## Example Output

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

$ chronicle ai today

AI Interactions Today
────────────────────────────────────────────────────────────
02:30 PM ✨ Gemini
   "How do I implement caching in Python?"
   → You can use functools.lru_cache decorator for function-level caching...
   ⏱ 2.3s
   ✓ Linked to commit abc1234

01:45 PM 🔮 Qwen
   "Review this authentication code"
   → The code looks good overall. Consider adding rate limiting...
   ⏱ 3.1s

$ chronicle ai-stats --days 7

AI Tool Usage (Last 7 days)
════════════════════════════════════════════════════════════
┏━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┓
┃ AI Tool  ┃  Interactions ┃   Percentage ┃  Avg Duration ┃
┡━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━┩
│ Gemini   │            15 │        65.2% │         2.4s  │
│          │               │ █████████… │               │
│ Qwen     │             8 │        34.8% │         3.2s  │
│          │               │ ██████░░░… │               │
└──────────┴───────────────┴──────────────┴───────────────┘

Total interactions: 23

$ chronicle timeline today

Combined Development Timeline
════════════════════════════════════════════════════════════
02:30 PM ✨ Gemini
   "How do I implement caching in Python?"

02:25 PM [abc1234] Add caching to API endpoints
   → api/cache.py
   → api/endpoints.py

01:45 PM 🔮 Qwen
   "Review this authentication code"

01:30 PM [def5678] Implement JWT authentication
   → auth/jwt.py
   → middleware/auth.py
```

## Roadmap

See [AI_SESSION_RECORDER_SPEC.md](./AI_SESSION_RECORDER_SPEC.md) for the complete specification and roadmap.

### Week 1 ✅
- [x] Initialize Python project
- [x] Set up SQLite database
- [x] Implement git commit monitoring
- [x] Build CLI with show/search commands

### Week 2 (In Progress)
- [ ] Create AI wrapper shell script
- [ ] Implement AI interaction tracking
- [ ] Link interactions to commits

### Week 3+
- [ ] Gemini summarization
- [ ] Automated daily jobs
- [ ] Next.js dashboard
- [ ] Export features

## License

MIT

## Author

Chandler Hardy

---

**Built with:** Claude Code (and tracked by Chronicle itself!)
