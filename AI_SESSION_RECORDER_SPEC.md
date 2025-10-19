# AI Session Recorder - Project Specification

## Project Overview
A development session recorder that tracks interactions across multiple AI tools (Claude Code, Gemini CLI, Qwen CLI), git commits, and file changes to create a unified development timeline with intelligent summarization.

## Problem Statement
Modern developers use multiple AI assistants, but:
- Each AI has no memory of what other AIs did
- No persistent record between sessions
- Hard to track decisions made across different tools
- Documentation becomes outdated quickly

## Solution
A local-first session recorder that:
1. Monitors AI interactions across multiple tools
2. Tracks git commits and file changes
3. Generates intelligent summaries at multiple time scales
4. Provides queryable development history
5. Auto-generates documentation

---

## Tech Stack

### Backend
- **Python 3.11+** - Core logic and CLI
- **FastAPI** - Web API for dashboard (optional Phase 2)
- **SQLite** - Local data storage
- **Git Python** - Git integration

### Frontend (Phase 2)
- **Next.js 15** - Web dashboard
- **TypeScript** - Type safety
- **Tailwind CSS** - Styling
- **Recharts** - Data visualization

### AI Integration
- **Gemini API** - For summarization (cheap/free)
- **Shell integration** - Wrapper scripts for CLI tools

---

## MVP Feature Set (Phase 1: 2-3 weeks)

### Core Features

#### 1. Git Commit Tracking ✅ Start Here
- Monitor git commits in watched directories
- Store: timestamp, SHA, message, files changed, author
- Link commits to potential AI interactions (based on timing)

**Database Schema:**
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

#### 2. AI Interaction Tracking
**Shell Wrapper Approach:**
```bash
# User runs:
ai-session gemini "design auth flow"
ai-session qwen "review this code"

# Wrapper logs interaction and passes through to actual CLI
```

**Database Schema:**
```sql
CREATE TABLE ai_interactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    ai_tool TEXT NOT NULL,  -- 'claude-code', 'gemini-cli', 'qwen-cli'
    prompt TEXT NOT NULL,
    response_summary TEXT,  -- First 500 chars
    files_mentioned TEXT,   -- JSON array
    duration_ms INTEGER,
    related_commit_id INTEGER,
    FOREIGN KEY (related_commit_id) REFERENCES commits(id)
);
```

#### 3. Daily Summarization
**Automated nightly job:**
- Reads all interactions from the day
- Uses Gemini to generate 200-word summary
- Stores in summaries table
- Optionally deletes raw data older than 7 days

**Database Schema:**
```sql
CREATE TABLE daily_summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL,
    summary TEXT NOT NULL,
    topics TEXT,  -- JSON array of topics
    files_affected TEXT,  -- JSON array
    commits_count INTEGER,
    ai_interactions_count INTEGER,
    key_decisions TEXT  -- JSON array
);
```

#### 4. CLI Query Interface
```bash
# Show today's activity
devsession show today

# Show last week
devsession show --days 7

# Search for topic
devsession search "authentication"

# Show AI tool usage
devsession stats --ai

# Generate summary
devsession summarize --yesterday
```

---

## Data Retention Strategy

### Hierarchical Storage
```
┌─────────────────────────────────────────┐
│ Level 1: Raw Data (7 days)             │
│ - Full prompts & responses              │
│ - Detailed file changes                 │
│ - Auto-deleted after 7 days             │
└─────────────────────────────────────────┘
           ↓ Summarize
┌─────────────────────────────────────────┐
│ Level 2: Daily Summaries (90 days)     │
│ - Key decisions                         │
│ - Files affected                        │
│ - Major changes                         │
└─────────────────────────────────────────┘
           ↓ Aggregate
┌─────────────────────────────────────────┐
│ Level 3: Weekly Digests (Forever)      │
│ - High-level overview                   │
│ - Major milestones                      │
│ - Project progress                      │
└─────────────────────────────────────────┘
```

### Size Estimates
- **Raw data**: ~50MB/day → Auto-deleted after 7 days
- **Daily summaries**: ~50KB/day → 1.5MB/month
- **Weekly digests**: ~10KB/week → 520KB/year

**Total storage for 1 year**: ~20MB (vs 18GB without summarization!)

---

## Implementation Phases

### Phase 1: Foundation (Week 1) ⭐ MVP
**Goal:** Basic tracking and querying

1. **Day 1-2: Project Setup**
   - Initialize Python project
   - Set up SQLite database with schema
   - Create basic CLI with Click/Typer

2. **Day 3-4: Git Integration**
   - Implement git commit monitoring
   - Create file watcher for repos
   - Test with multiple repositories

3. **Day 5-6: AI Wrapper**
   - Create shell wrapper script
   - Test with gemini-cli and qwen-cli
   - Store interactions in database

4. **Day 7: Basic CLI**
   - `devsession show` command
   - `devsession search` command
   - Output formatted markdown

### Phase 2: Summarization (Week 2)
**Goal:** Intelligent compression

1. **Day 8-9: Gemini Integration**
   - Set up Gemini API
   - Create summarization prompt
   - Test summary quality

2. **Day 10-11: Auto-summarization**
   - Implement nightly job (cron/systemd)
   - Create data retention policies
   - Test deletion of old data

3. **Day 12-14: Enhanced Queries**
   - Timeline view
   - Topic extraction
   - Session detection (group related work)

### Phase 3: Dashboard (Week 3+)
**Goal:** Visual interface

1. **Web Dashboard**
   - Next.js app with timeline view
   - Filter by AI tool, date, topic
   - Search functionality

2. **Analytics**
   - AI tool usage charts
   - Productivity metrics
   - File change heatmap

3. **Export Features**
   - Generate blog posts
   - Auto-update CLAUDE.md
   - Create project README

---

## File Structure

```
ai-session-recorder/
├── backend/
│   ├── main.py              # CLI entry point
│   ├── database/
│   │   ├── __init__.py
│   │   ├── models.py        # SQLAlchemy models
│   │   └── migrations/
│   ├── services/
│   │   ├── git_monitor.py   # Git tracking
│   │   ├── ai_wrapper.py    # AI CLI wrapper
│   │   ├── summarizer.py    # Gemini summarization
│   │   └── query.py         # Query interface
│   ├── cli/
│   │   ├── commands.py      # CLI commands
│   │   └── formatters.py    # Output formatting
│   └── config.py            # Configuration
├── scripts/
│   ├── ai-session           # Shell wrapper script
│   └── install.sh           # Installation script
├── frontend/                # Phase 3
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   └── lib/
│   └── package.json
├── tests/
│   ├── test_git_monitor.py
│   ├── test_ai_wrapper.py
│   └── test_summarizer.py
├── requirements.txt
├── pyproject.toml
├── README.md
└── CLAUDE.md
```

---

## Configuration File

**~/.ai-session/config.yaml**
```yaml
# Repositories to monitor
repositories:
  - /Users/chandlerhardy/repos/portfolio-website
  - /Users/chandlerhardy/repos/crooked-finger

# Retention policies
retention:
  raw_data_days: 7
  summaries_days: 90
  keep_forever:
    - conversations_with_commits
    - tagged_important

# AI tools
ai_tools:
  gemini:
    api_key: ${GEMINI_API_KEY}
    model: gemini-2.0-flash-exp
  claude:
    detect_via_git: true
  qwen:
    cli_path: /usr/local/bin/qwen

# Summarization
summarization:
  enabled: true
  schedule: "0 2 * * *"  # 2 AM daily
  max_summary_length: 500
```

---

## Example Outputs

### Daily Summary
```markdown
# Development Session - January 19, 2025

## Overview
Worked on portfolio website project detail pages and AI session recorder planning.

## AI Tools Used
- **Claude Code**: 5 interactions (3.2 hours)
- **Gemini CLI**: 2 interactions (0.5 hours)

## Key Changes
### Portfolio Website
- Created dynamic project detail pages (/projects/[slug])
- Added gradient backgrounds for project cards
- Updated skills section (added Python, FastAPI)
- **Commits**: 3 (abc123, def456, xyz789)
- **Files**: Projects.tsx, Skills.tsx, projects.ts

## Decisions Made
1. Use separate image scales for home page vs detail pages
2. Gradient background (gray → blue) for CryptAssist logo
3. Remove Firebase and AWS from skills list

## Next Steps
- Start building AI Session Recorder
- Add project screenshots to detail pages
```

### Query Examples
```bash
$ devsession show today
📅 Today - January 19, 2025
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🤖 Claude Code (10:00 AM)
   "Add project detail pages"
   → Created src/app/projects/[slug]/page.tsx
   → Commit: abc123

🤖 Claude Code (2:30 PM)
   "Update skills section"
   → Modified components/Skills.tsx
   → Commit: def456

📊 Stats:
   AI Interactions: 7
   Commits: 3
   Files Changed: 8
   Duration: 4.5 hours

$ devsession search "authentication"
🔍 Found 5 results for "authentication"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Jan 18 - Gemini CLI
   "Design JWT authentication flow"

Jan 18 - Claude Code
   "Implement auth middleware"
   → auth.ts, middleware.ts

$ devsession stats --ai
📊 AI Tool Usage (Last 30 days)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Claude Code:  ████████████████ 65% (142 interactions)
Gemini CLI:   ██████░░░░░░░░░░ 25% (54 interactions)
Qwen CLI:     ███░░░░░░░░░░░░░ 10% (22 interactions)
```

---

## Installation & Setup

### Prerequisites
```bash
# Python 3.11+
python --version

# Git
git --version

# AI CLIs (optional)
gemini --version
qwen --version
```

### Quick Start
```bash
# Clone repo
git clone https://github.com/ChandlerHardy/ai-session-recorder
cd ai-session-recorder

# Install
pip install -e .

# Initialize
devsession init

# Add repositories to monitor
devsession add-repo /path/to/your/project

# Start recording
# (Runs in background, monitoring git commits)

# Use AI wrapper
ai-session gemini "your prompt here"
ai-session qwen "your prompt here"

# View session
devsession show today
```

---

## Future Enhancements (Post-MVP)

### Advanced Features
1. **Team Collaboration**
   - Share session summaries with team
   - Compare AI usage across developers
   - Best practices library

2. **Smart Notifications**
   - "You haven't committed in 2 hours"
   - "Similar problem solved last week"
   - "This file changed 5 times today"

3. **Integration Ecosystem**
   - VS Code extension
   - Slack bot for daily summaries
   - GitHub action for PR descriptions
   - Jira/Linear integration

4. **Advanced Analytics**
   - Code quality trends
   - AI effectiveness metrics
   - Productivity patterns
   - Cost tracking (API usage)

5. **Knowledge Graph**
   - Build relationships between files, features, decisions
   - "Show me everything related to authentication"
   - Visual dependency maps

---

## Success Metrics

### Technical
- ✅ Captures 95%+ of git commits
- ✅ Logs AI interactions with <100ms overhead
- ✅ Summaries generated in <30 seconds
- ✅ Database size stays under 50MB/year

### User Experience
- ✅ Can answer "what did I do yesterday?" in <5 seconds
- ✅ Finds specific past decisions in <10 seconds
- ✅ Generates useful documentation automatically
- ✅ Provides context across AI sessions

### Portfolio Impact
- ✅ Demonstrates Python backend skills
- ✅ Shows AI integration expertise
- ✅ Proves ability to identify & solve real problems
- ✅ Creates actual value (tool you'll use daily)

---

## Development Notes

### Why This Is a Great Portfolio Project

1. **Solves Real Problem**: You experience this pain daily
2. **Emerging Technology**: AI-assisted dev is brand new
3. **Full-Stack Skills**: Backend (Python/FastAPI), Frontend (Next.js), AI integration
4. **Meta Appeal**: Tool for building tools
5. **Actually Useful**: You'll use it to document building itself
6. **Unique**: Nothing else like it exists
7. **Expandable**: Clear path from MVP to production product

### Potential Challenges

1. **Shell Integration**: Getting wrapper to work seamlessly
   - Solution: Start simple, iterate based on usage

2. **Summarization Quality**: AI summaries might miss important details
   - Solution: Iterate on prompts, allow manual editing

3. **Performance**: Monitoring could slow down git operations
   - Solution: Use async operations, minimal overhead

4. **Privacy**: Storing sensitive prompts/code
   - Solution: Local-first, built-in filtering, encryption option

---

## Getting Started Checklist

### Before You Start
- [ ] Create new GitHub repo: `ai-session-recorder`
- [ ] Set up Python virtual environment
- [ ] Get Gemini API key (free tier)
- [ ] Read this spec thoroughly

### Week 1 Tasks
- [ ] Initialize Python project with proper structure
- [ ] Create SQLite schema
- [ ] Implement basic git monitoring
- [ ] Build simple CLI with `show` command
- [ ] Test with portfolio-website repo

### Week 2 Tasks
- [ ] Create AI wrapper shell script
- [ ] Test with gemini-cli and qwen-cli
- [ ] Implement Gemini summarization
- [ ] Add automated daily job
- [ ] Test data retention policies

### Week 3+ Tasks
- [ ] Build Next.js dashboard
- [ ] Add timeline visualization
- [ ] Create export features
- [ ] Write comprehensive README
- [ ] Deploy and use daily

---

## Resources

### Documentation
- [Git Python Library](https://gitpython.readthedocs.io/)
- [Gemini API Docs](https://ai.google.dev/docs)
- [SQLite Best Practices](https://sqlite.org/bestpractice.html)
- [Click CLI Framework](https://click.palletsprojects.com/)

### Similar Projects (for inspiration)
- [git-journal](https://github.com/saschagrunert/git-journal) - Git commit analysis
- [WakaTime](https://wakatime.com/) - Coding activity tracking
- [ActivityWatch](https://activitywatch.net/) - Time tracking

### AI Prompts for Development
```
"Help me implement git commit monitoring in Python using GitPython"
"Create a SQLite schema for storing AI interactions with summaries"
"Write a bash wrapper script that logs commands and passes through to CLI"
"Design a prompt for Gemini to summarize a day of development activity"
```

---

## License & Attribution

**License**: MIT (open source)
**Author**: Chandler Hardy
**Built With**: Claude Code, Gemini, Qwen (documented via this tool!)

---

**Ready to start? Begin with Week 1 tasks and build iteratively!**

*This spec will evolve as you build - update it regularly to reflect learnings and changes.*
